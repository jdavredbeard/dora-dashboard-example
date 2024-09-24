import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

vpc = awsx.ec2.Vpc(
    "vpc",
    cidr_block="10.0.0.0/24",
    nat_gateways=awsx.ec2.NatGatewayConfigurationArgs(
        strategy=awsx.ec2.NatGatewayStrategy.SINGLE
    )
)

alb_security_group = aws.ec2.SecurityGroup(
    "alb-security-group",
    vpc_id=vpc.vpc_id,
    description="ALB",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        description="Allow HTTP from anywhere",
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=["0.0.0.0/0"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        description="Allow HTTP to VPC",
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=[vpc.vpc.cidr_block],
    ),
    aws.ec2.SecurityGroupEgressArgs(
        description="Allow HTTP to VPC",
        protocol="tcp",
        from_port=5000,
        to_port=5000,
        cidr_blocks=[vpc.vpc.cidr_block],
    )],
    tags={
        "Name": "ALB"
    },
)

alb = aws.lb.LoadBalancer(
    "app-lb",
    security_groups=[alb_security_group.id],
    subnets=vpc.public_subnet_ids,
)

target_group = aws.lb.TargetGroup(
    "app-tg",
    port=5000,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc.vpc_id,
)

http_listener = aws.lb.Listener(
    "http-listener",
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn
    }]
)

pulumi.export("vpc_id", vpc.vpc_id)
pulumi.export("vpc_cidr_block", vpc.vpc.cidr_block)
pulumi.export("private_subnet_ids", vpc.private_subnet_ids)
pulumi.export("target_group_arn", target_group.arn)
pulumi.export("lb_security_group_id", alb_security_group.id)
pulumi.export("lb_url", pulumi.Output.concat("http://", alb.dns_name))