variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = "ghcr.io"
}

variable "REPO_OWNER" {
  default = "reonokiy"
}

group "default" {
  targets = ["simple-backup", "simple-backup-operator"]
}

target "simple-backup" {
  context    = "."
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/${REPO_OWNER}/simple-backup:${TAG}",
    "${REGISTRY}/${REPO_OWNER}/simple-backup:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "simple-backup-operator" {
  context    = "./helm/simple-backup-operator/operator"
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/${REPO_OWNER}/simple-backup-operator:${TAG}",
    "${REGISTRY}/${REPO_OWNER}/simple-backup-operator:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
}
