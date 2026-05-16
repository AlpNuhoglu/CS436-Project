{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "ECS API — CPU & Memory",
        "region": "eu-central-1",
        "metrics": [
          ["AWS/ECS", "CPUUtilization",    "ClusterName", "${project}", "ServiceName", "${project}-api", {"label": "CPU %"}],
          ["AWS/ECS", "MemoryUtilization", "ClusterName", "${project}", "ServiceName", "${project}-api", {"label": "Memory %"}]
        ],
        "period": 60,
        "stat": "Average",
        "yAxis": {"left": {"min": 0, "max": 100}}
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "ALB — Request Count & 5xx Errors",
        "region": "eu-central-1",
        "metrics": [
          ["AWS/ApplicationELB", "RequestCount",              "LoadBalancer", "app/dersforumu-alb/cabde2edfdc7f590", {"label": "Requests", "stat": "Sum"}],
          ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/dersforumu-alb/cabde2edfdc7f590", {"label": "5xx Errors", "stat": "Sum", "color": "#d62728"}]
        ],
        "period": 60,
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "ALB — Target Response Time (p95)",
        "region": "eu-central-1",
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/dersforumu-alb/cabde2edfdc7f590", {"label": "p95 Latency (s)", "stat": "p95"}]
        ],
        "period": 60,
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "RDS — CPU & Connections",
        "region": "eu-central-1",
        "metrics": [
          ["AWS/RDS", "CPUUtilization",     "DBInstanceIdentifier", "${project}-postgres", {"label": "CPU %",       "stat": "Average"}],
          ["AWS/RDS", "DatabaseConnections","DBInstanceIdentifier", "${project}-postgres", {"label": "Connections", "stat": "Average", "yAxis": "right"}]
        ],
        "period": 60,
        "yAxis": {"left": {"min": 0, "max": 100}, "right": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 12, "width": 12, "height": 6,
      "properties": {
        "title": "Redis — CPU & Memory",
        "region": "eu-central-1",
        "metrics": [
          ["AWS/ElastiCache", "EngineCPUUtilization",         "ReplicationGroupId", "${project}-redis", {"label": "CPU %",    "stat": "Average"}],
          ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage","ReplicationGroupId", "${project}-redis", {"label": "Memory %", "stat": "Average"}]
        ],
        "period": 60,
        "yAxis": {"left": {"min": 0, "max": 100}}
      }
    },
    {
      "type": "alarm",
      "x": 12, "y": 12, "width": 12, "height": 6,
      "properties": {
        "title": "Active Alarms",
        "alarms": [
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-api-cpu-high",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-api-memory-high",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-api-task-count-low",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-alb-5xx-high",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-alb-unhealthy-hosts",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-db-cpu-high",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-db-free-storage-low",
          "arn:aws:cloudwatch:eu-central-1:${account_id}:alarm:${project}-redis-cpu-high"
        ]
      }
    }
  ]
}
