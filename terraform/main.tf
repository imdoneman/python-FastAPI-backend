
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for the Tea House API server"
  type        = string
  default     = "ap-south-1"
}

variable "ami_id" {
  description = "Amazon Linux 2023 AMI ID for the target region"
  type        = string
  default     = "ami-04394a3a96907e9ec"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of the existing EC2 key pair"
  type        = string
  default     = "FastAPI_key"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to connect to SSH on the EC2 instance"
  type        = string
  default     = "0.0.0.0/0"
}

resource "aws_security_group" "tea_house_sg" {
  name        = "tea_house_sg"
  description = "Allow SSH administration and Tea House API access"

  tags = {
    Name = "tea-house-api-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = var.ssh_allowed_cidr
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
  description       = "SSH access for Jenkins and Ansible"
}

resource "aws_vpc_security_group_ingress_rule" "allow_fastapi" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 8000
  ip_protocol       = "tcp"
  to_port           = 8000
  description       = "Public Tea House API access"
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Outbound access for package and image downloads"
}

resource "aws_instance" "tea_house_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.tea_house_sg.id]

  tags = {
    Name = "Tea-App-Server"
  }
}

output "server_public_ip" {
  description = "Public IP address of the Tea House API server"
  value       = aws_instance.tea_house_server.public_ip
}

output "ssh_username" {
  description = "Default SSH username for Amazon Linux 2023"
  value       = "ec2-user"
}
