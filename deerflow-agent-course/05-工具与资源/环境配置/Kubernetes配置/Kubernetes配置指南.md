# ☸️ DeerFlow Kubernetes 配置

## 📁 目录结构
```
Kubernetes配置/
├── 基础配置/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   └── secret.yaml
├── 部署配置/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── Ingress/
│   └── ingress.yaml
├── 存储/
│   └── pvc.yaml
└── Helm/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
```

## 1. 命名空间

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deerflow
  labels:
    name: deerflow
    environment: production
```

## 2. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deerflow-config
  namespace: deerflow
data:
  # 应用配置
  APP_ENV: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  
  # 数据库配置
  DB_POOL_SIZE: "20"
  DB_MAX_OVERFLOW: "10"
  DB_POOL_TIMEOUT: "30"
  
  # Redis配置
  REDIS_DB: "0"
  REDIS_MAX_CONNECTIONS: "50"
  
  # Agent配置
  AGENT_MAX_ITERATIONS: "100"
  AGENT_TIMEOUT: "300"
  SANDBOX_TIMEOUT: "300"
  
  # 中间件链
  MIDDLEWARE_CHAIN: "ThreadDataMiddleware,UploadsMiddleware,SandboxMiddleware,ToolErrorHandlingMiddleware"
```

## 3. Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: deerflow-secrets
  namespace: deerflow
type: Opaque
stringData:
  # API密钥
  OPENAI_API_KEY: "sk-xxxxx"
  ANTHROPIC_API_KEY: "sk-ant-xxxxx"
  
  # 数据库
  DB_PASSWORD: "your-db-password"
  
  # JWT
  JWT_SECRET_KEY: "your-jwt-secret"
  JWT_ALGORITHM: "HS256"
  
  # 加密
  ENCRYPTION_KEY: "your-32-byte-encryption-key"
```

## 4. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deerflow-api
  namespace: deerflow
  labels:
    app: deerflow-api
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: deerflow-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: deerflow-api
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: deerflow-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: deerflow:${VERSION:-latest}
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: deerflow-config
            - secretRef:
                name: deerflow-secrets
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: deerflow-secrets
                  key: DATABASE_URL
            - name: REDIS_URL
              value: "redis://redis:6379/0"
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 4Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: deerflow-api
                topologyKey: kubernetes.io/hostname
      tolerations:
        - key: "node-type"
          operator: "Equal"
          value: "application"
          effect: "NoSchedule"
```

## 5. Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: deerflow-api
  namespace: deerflow
  labels:
    app: deerflow-api
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: deerflow-api
---
apiVersion: v1
kind: Service
metadata:
  name: deerflow-api-headless
  namespace: deerflow
  labels:
    app: deerflow-api
spec:
  type: ClusterIP
  clusterIP: None
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: deerflow-api
```

## 6. HPA (水平自动扩缩容)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: deerflow-api-hpa
  namespace: deerflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: deerflow-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

## 7. Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deerflow-ingress
  namespace: deerflow
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-write-timeout: "300"
    nginx.ingress.kubernetes.io/websocket-services: "deerflow-api"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$request_id"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.deerflow.example.com
      secretName: deerflow-tls
  rules:
    - host: api.deerflow.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: deerflow-api
                port:
                  number: 80
```

## 8. PodDisruptionBudget

```yaml
# pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: deerflow-api-pdb
  namespace: deerflow
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: deerflow-api
```

## 9. ServiceAccount 和 RBAC

```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deerflow-sa
  namespace: deerflow
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deerflow-role
  namespace: deerflow
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "create", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deerflow-rolebinding
  namespace: deerflow
subjects:
  - kind: ServiceAccount
    name: deerflow-sa
    namespace: deerflow
roleRef:
  kind: Role
  name: deerflow-role
  apiGroup: rbac.authorization.k8s.io
```

## 10. Prometheus ServiceMonitor

```yaml
# servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: deerflow-monitor
  namespace: deerflow
  labels:
    app: deerflow-api
spec:
  selector:
    matchLabels:
      app: deerflow-api
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
      scrapeTimeout: 10s
  namespaceSelector:
    matchNames:
      - deerflow
```

## 11. Helm Chart

```yaml
# Chart.yaml
apiVersion: v2
name: deerflow
description: DeerFlow AI Agent Platform Helm Chart
type: application
version: 1.0.0
appVersion: "2.0.0"
keywords:
  - ai
  - agent
  - langchain
  - langgraph
maintainers:
  - name: DeerFlow Team
```

```yaml
# values.yaml
# DeerFlow Helm Chart Values

replicaCount: 3

image:
  repository: deerflow
  tag: latest
  pullPolicy: Always

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  host: api.deerflow.example.com
  tls:
    enabled: true
    secretName: deerflow-tls

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

config:
  appEnv: production
  logLevel: INFO
  agentMaxIterations: 100
  sandboxTimeout: 300

persistence:
  enabled: true
  storageClass: standard
  size: 10Gi

redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: true
    password: ""

postgresql:
  enabled: true
  auth:
    database: deerflow
    username: deerflow
    password: ""

monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

## 12. 部署脚本

```bash
#!/bin/bash
# deploy.sh - DeerFlow Kubernetes 部署脚本

set -e

NAMESPACE="deerflow"
VERSION="${1:-latest}"

echo "=== Deploying DeerFlow v${VERSION} to ${NAMESPACE} ==="

# 创建命名空间
kubectl apply -f namespace.yaml

# 部署配置
kubectl apply -f configmap.yaml -n ${NAMESPACE}
kubectl apply -f secret.yaml -n ${NAMESPACE}

# 部署应用
kubectl apply -f deployment.yaml -n ${NAMESPACE}
kubectl apply -f service.yaml -n ${NAMESPACE}
kubectl apply -f hpa.yaml -n ${NAMESPACE}
kubectl apply -f pdb.yaml -n ${NAMESPACE}

# 部署Ingress
kubectl apply -f ingress.yaml -n ${NAMESPACE}

# 等待部署完成
echo "Waiting for rollout..."
kubectl rollout status deployment/deerflow-api -n ${NAMESPACE}

# 显示状态
kubectl get pods -n ${NAMESPACE} -l app=deerflow-api

echo "=== Deployment complete ==="
```

---

## 📊 资源规划参考

| 组件 | CPU请求 | CPU限制 | 内存请求 | 内存限制 | 副本数 |
|------|---------|---------|----------|----------|--------|
| API | 250m | 2000m | 512Mi | 4Gi | 3-20 |
| Sandbox | 100m | 1000m | 256Mi | 1Gi | 2-10 |
| Redis | 100m | 500m | 256Mi | 1Gi | 1 |
| PostgreSQL | 250m | 1000m | 512Mi | 2Gi | 1 |

---

**下一步**：查看监控配置
