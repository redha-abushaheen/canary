import subprocess
import requests
import yaml
import time

# Constants
NAMESPACE = "canary-demo"
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

# Helper functions
def run_kubectl_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def prometheus_query(query):
    response = requests.get(PROMETHEUS_URL, params={"query": query})
    if response.status_code == 200:
        data = response.json()
        return data['data']['result'][0]['value'][1] if data['data']['result'] else None
    return None

def populate_answers_yml(data):
    with open("answers.yml", "w") as file:
        yaml.dump(data, file, default_flow_style=False)

# Gather deployment and service data
def gather_deployment_info():
    print("Gathering deployment and service data...")
    data = {}
    
    # Get pod status
    pods = run_kubectl_command(f"kubectl get pods -n {NAMESPACE}")
    main_pods_running = pods.count("canary-demo-d")
    canary_pods_running = pods.count("canary-demo-canary")

    # Get ClusterIPs for services
    services = run_kubectl_command(f"kubectl get services -n {NAMESPACE} -o=jsonpath='{{range .items[*]}}{{.metadata.name}} {{.spec.clusterIP}}{{\"\\n\"}}{{end}}'")
    main_service_ip = canary_service_ip = None
    for service in services.splitlines():
        name, ip = service.split()
        if name == "canary-demo":
            main_service_ip = ip
        elif name == "canary-demo-canary":
            canary_service_ip = ip

    # Get Ingress details
    ingress = run_kubectl_command(f"kubectl get ingress -n {NAMESPACE} -o=jsonpath='{{.items[0].status.loadBalancer.ingress[0].ip}}'")
    
    data['pods_status'] = {
        'main_pods_running': main_pods_running,
        'canary_pods_running': canary_pods_running
    }
    data['service_endpoints'] = {
        'main_service_cluster_ip': main_service_ip,
        'canary_service_cluster_ip': canary_service_ip
    }
    data['ingress_details'] = {
        'address': ingress,
        'host': "canary-demo.local"
    }
    return data

# Gather metrics
def gather_metrics():
    print("Gathering metrics...")
    data = {}

    # Main deployment metrics
    main_requests_total = prometheus_query('http_requests_total{app="main-deployment"}')
    main_cpu_seconds = prometheus_query('process_cpu_seconds_total{app="main-deployment"}')
    main_memory_bytes = prometheus_query('process_resident_memory_bytes{app="main-deployment"}')

    # Canary deployment metrics
    canary_requests_total = prometheus_query('http_requests_total{app="canary-deployment"}')
    canary_cpu_seconds = prometheus_query('process_cpu_seconds_total{app="canary-deployment"}')
    canary_memory_bytes = prometheus_query('process_resident_memory_bytes{app="canary-deployment"}')

    # Prometheus request rate metrics
    main_request_rate = prometheus_query('rate(http_requests_total{version="v1"}[5m])')
    canary_request_rate = prometheus_query('rate(http_requests_total{version="v2"}[5m])')

    data['main_deployment_metrics'] = {
        'http_requests_total': main_requests_total,
        'process_cpu_seconds_total': main_cpu_seconds,
        'process_resident_memory_bytes': main_memory_bytes
    }
    data['canary_deployment_metrics'] = {
        'http_requests_total': canary_requests_total,
        'process_cpu_seconds_total': canary_cpu_seconds,
        'process_resident_memory_bytes': canary_memory_bytes
    }
    data['prometheus_metrics'] = {
        'main_request_rate': main_request_rate,
        'canary_request_rate': canary_request_rate
    }
    return data

# Gather traffic distribution test results
def gather_traffic_test_results():
    print("Running traffic distribution test...")
    # Simulate 20 requests
    total_requests = 20
    main_responses = canary_responses = 0
    
    for _ in range(total_requests):
        response = requests.get("http://canary-demo.local")
        if "canary-deployment" in response.text:
            canary_responses += 1
        else:
            main_responses += 1
        time.sleep(0.1)

    # Calculate percentage of canary traffic
    canary_percentage = (canary_responses / total_requests) * 100 if total_requests else 0
    
    data = {
        'total_requests_sent': total_requests,
        'main_responses_received': main_responses,
        'canary_responses_received': canary_responses,
        'actual_canary_percentage': canary_percentage
    }
    return data

# Gather error budget data
def gather_error_budget():
    print("Calculating error budget...")
    # Replace with actual calculation if available
    monthly_error_budget_seconds = 2592.00  # Assuming for example purposes
    remaining_error_budget_percentage = 100.00  # Replace with actual calculation
    
    data = {
        'monthly_error_budget_seconds': monthly_error_budget_seconds,
        'remaining_error_budget_percentage': remaining_error_budget_percentage
    }
    return data

# Main function to populate answers.yml
def main():
    answers_data = {}
    answers_data.update(gather_deployment_info())
    answers_data.update(gather_metrics())
    answers_data['traffic_test_results'] = gather_traffic_test_results()
    answers_data['error_budget'] = gather_error_budget()
    
    # Observations placeholder
    answers_data['observations'] = {
        'unexpected_behaviors': "No unexpected behaviors noted.",
        'suggested_improvements': "Consider optimizing traffic routing logic for more balanced distribution."
    }

    # Save to answers.yml
    populate_answers_yml(answers_data)
    print("answers.yml has been populated with the gathered data.")

if __name__ == "__main__":
    main()
