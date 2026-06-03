terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# 1. Fetch the Default, Free AWS VPC
data "aws_vpc" "default" {
  default = true
}

# 2. Fetch the default public subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# 3. The Bare-Minimum, Eviction-Proof EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "practice-tea-cluster"
  cluster_version = "1.30"

  vpc_id     = data.aws_vpc.default.id
  subnet_ids = data.aws_subnets.default.ids

  cluster_endpoint_public_access = true
  
  eks_managed_node_groups = {
    stable_node = {
      min_size     = 1
      max_size     = 1
      desired_size = 1

      instance_types = ["t3.medium"] 
      
      # Changed to ON_DEMAND to guarantee 100% stability during your demo
      capacity_type  = "ON_DEMAND"        
    }
  }

  enable_cluster_creator_admin_permissions = true
}