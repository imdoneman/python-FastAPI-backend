terraform {
  required_version = "=>1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# 1. Create the Security Group Shell Container
resource "aws_security_group" "tea_house_sg" {
  name        = "tea_house_sg"
  description = "allow ssh traffic for ansible and web traffic for FastAPI"

  tags = {
    name = "tea_house_sg"
  }
}

# 2. Modern Ingress Rule: SSH Port for Configuration Management (Ansible)
resource "aws_vpc_security_group_ingress_rule" "allow_ssh" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = "152.59.158.72/32"
  from_port         = 22
  ip_protocol       = tcp
  to_port           = 22
}

# 3. Modern Ingress Rule: FastAPI Web Traffic Application Port
resource "aws_vpc_security_group_ingress_rule" "allow_FastAPI" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 8000
  ip_protocol       = tcp
  to_port           = 8000
}

# 4. Modern Egress Rule: Outbound Internet Access (For downloading updates/Docker images)
resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.tea_house_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# 5. Virtual Server Provisioning (EC2)
resource "aws_instance" "tea_house_server" {
  ami           = "ami-09ed39e30153c3bf9"
  instance_type = "t2.micro"
  key_name      = "AKIA4LRIXXJ6CJUPAVXI"

  vpc_security_group_ids = [aws_security_group.tea_house_sg.id]

  tags = {
    name = "Tea-App-Server"
  }
  # Outputs the newly created IP address straight to your Ansible hosts file
  provisioner "local-exec" {
    command = "echo ${self.public_ip} > ../ansible/hosts"
  }
}

output "server_public_ip" {
  value       = aws_instance.tea_house_server.public_ip
  description = "The public ip address assigned to the Cloud server instance"
}
