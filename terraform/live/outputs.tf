output "public_ip" {
  value = module.app_server.public_ip
}

output "app_url" {
  value = "http://${module.app_server.public_ip}"
}
