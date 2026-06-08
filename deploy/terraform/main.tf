terraform {
  required_providers {
    docker = { source = "kreuzwerker/docker", version = "~> 3.0" }
  }
}
# Minimal container deploy. Swap the provider block for aws_ecs_service,
# azurerm_container_app, or google_cloud_run_v2_service as needed.
provider "docker" {}
resource "docker_image" "hl7tap" { name = "ghcr.io/cognis-digital/hl7tap:latest" }
resource "docker_container" "hl7tap" {
  name  = "hl7tap"
  image = docker_image.hl7tap.image_id
  ports { internal = 8000 external = 8000 }
}
