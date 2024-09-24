import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import pulumi_docker_build as docker_build
import json

org = pulumi.get_organization()
networking_stack = pulumi.StackReference(f"{org}/networking/dev")

# Create ECR repository to store image
ecr_repository = aws.ecr.Repository("ecr-repository", force_delete=True)
auth_token = aws.ecr.get_authorization_token_output(registry_id=ecr_repository.registry_id)

# Build image and upload to ECR repository
my_image = docker_build.Image("my-image",
    cache_from=[{
        "registry": {
            "ref": ecr_repository.repository_url.apply(lambda repository_url: f"{repository_url}:cache"),
        },
    }],
    cache_to=[{
        "registry": {
            "image_manifest": True,
            "oci_media_types": True,
            "ref": ecr_repository.repository_url.apply(lambda repository_url: f"{repository_url}:cache"),
        },
    }],
    context={
        "location": "../erroring-app",
    },
    push=True,
    registries=[{
        "address": ecr_repository.repository_url,
        "password": auth_token.password,
        "username": auth_token.user_name,
    }],
    tags=[ecr_repository.repository_url.apply(lambda repository_url: f"{repository_url}:latest")])


cluster = aws.ecs.Cluster("cluster")

role = aws.iam.Role(
    "task-exec-role",
    assume_role_policy=json.dumps({
        "Version": "2008-10-17",
        "Statement": [{
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
        }]
    }),
)

aws.iam.RolePolicyAttachment(
    "task-exec-policy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
)

task_definition = aws.ecs.TaskDefinition(
    "app-task",
    family="fargate-task-definition",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=pulumi.Output.json_dumps([{
        "name": "my-app",
        "image": my_image.ref,
        "portMappings": [{
            "containerPort": 5000,
            "hostPort": 5000,
            "protocol": "tcp"
        }]
    }])
)

service_security_group = aws.ec2.SecurityGroup(
    "service-security-group",
    vpc_id=networking_stack.get_output("vpc_id"),
    description="erroring-app-service",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        description="Allow HTTP from the LB security group",
        protocol="tcp",
        from_port=5000,
        to_port=5000,
        security_groups=[networking_stack.get_output("lb_security_group_id")]
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        description="Allow HTTPS to anywhere (to pull container images)",
        protocol="tcp",
        from_port=443,
        to_port=443,
        cidr_blocks=["0.0.0.0/0"],
    )],)

aws.ecs.Service(
    "erroring-app-svc",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_definition.arn,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        assign_public_ip=False,
        subnets=networking_stack.get_output("private_subnet_ids"),
        security_groups=[service_security_group.id],
    ),
    load_balancers=[aws.ecs.ServiceLoadBalancerArgs(
        target_group_arn=networking_stack.get_output("target_group_arn"),
        container_name="my-app",
        container_port=5000,
    )],
)

pulumi.export("ref", my_image.ref)
pulumi.export("url", networking_stack.get_output("lb_url"))