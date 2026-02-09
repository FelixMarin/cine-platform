# 🟦 **1. Aplicar, actualizar y borrar YAML**

### Aplicar un archivo YAML
```
kubectl apply -f k3s/<archivo>.yaml
```

### Aplicar toda la carpeta
```
kubectl apply -f k3s/
```

### Borrar un recurso
```
kubectl delete -f k3s/<archivo>.yaml
```

### Ver qué se aplicará antes de aplicarlo
```
kubectl diff -f k3s/
```

---

# 🟦 **2. Ver estado del clúster**

### Ver pods del namespace cine
```
kubectl get pods -n cine
```

### Ver deployments
```
kubectl get deploy -n cine
```

### Ver servicios
```
kubectl get svc -n cine
```

### Ver PVCs
```
kubectl get pvc -n cine
```

### Ver todo lo del namespace
```
kubectl get all -n cine
```

---

# 🟦 **3. Información detallada**

### Describir un pod
```
kubectl describe pod <nombre> -n cine
```

### Describir un deployment
```
kubectl describe deploy cine-platform -n cine
```

### Describir un servicio
```
kubectl describe svc pocketbase -n cine
```

---

# 🟦 **4. Logs (cine‑platform y PocketBase)**

### Logs de cine‑platform
```
kubectl logs deploy/cine-platform -n cine
```

### Logs de PocketBase
```
kubectl logs deploy/pocketbase -n cine
```

### Logs en tiempo real
```
kubectl logs -f deploy/cine-platform -n cine
```

---

# 🟦 **5. Entrar dentro de un pod**

### Shell dentro de cine‑platform
```
kubectl exec -n cine -it deploy/cine-platform -- sh
```

### Shell dentro de PocketBase
```
kubectl exec -n cine -it deploy/pocketbase -- sh
```

### Shell dentro de un pod concreto
```
kubectl exec -n cine -it pod/<nombre> -- sh
```

---

# 🟦 **6. Port‑forward (para acceder al panel de PocketBase)**

### PocketBase panel
```
kubectl port-forward -n cine deploy/pocketbase 8070:8070
```

Acceso:
```
http://localhost:8070/_/
```

### cine‑platform (si quieres probarlo localmente)
```
kubectl port-forward -n cine deploy/cine-platform 5000:5000
```

---

# 🟦 **7. Reiniciar aplicaciones**

### Reiniciar cine‑platform
```
kubectl rollout restart deploy/cine-platform -n cine
```

### Reiniciar PocketBase
```
kubectl rollout restart deploy/pocketbase -n cine
```

---

# 🟦 **8. Crear pods temporales para pruebas**

### Pod Alpine para probar curl/wget
```
kubectl run testbox -n cine --rm -it --image=alpine -- sh
```

Dentro:
```
apk add curl
```

---

# 🟦 **9. Comandos útiles para depuración**

### Ver eventos del namespace
```
kubectl get events -n cine --sort-by=.metadata.creationTimestamp
```

### Ver recursos consumidos
```
kubectl top pods -n cine
```

### Ver nodos
```
kubectl get nodes -o wide
```

---

# 🟦 **10. Comandos específicos para tus apps**

## 🔹 Probar PocketBase desde dentro del clúster
```
curl http://pocketbase.cine.svc.cluster.local:8070/api/health
```

## 🔹 Probar login en PocketBase
```
curl -X POST "http://pocketbase.cine.svc.cluster.local:8070/api/collections/users/auth-with-password" \
  -H "Content-Type: application/json" \
  -d '{"identity":"EMAIL","password":"PASSWORD"}'
```

## 🔹 Ver variables de entorno de cine‑platform
```
kubectl exec -n cine -it deploy/cine-platform -- sh
echo $POCKETBASE_URL
```

---

# 🟦 **11. Gestión de namespaces**

### Ver namespaces
```
kubectl get ns
```

### Crear namespace
```
kubectl create ns cine
```

### Borrar namespace
```
kubectl delete ns cine
```

---

# 🟦 **12. Limpieza y mantenimiento**

### Borrar un pod (se recrea solo)
```
kubectl delete pod <nombre> -n cine
```

### Borrar un deployment
```
kubectl delete deploy cine-platform -n cine
```

### Borrar un servicio
```
kubectl delete svc cine-platform-service -n cine
```

---

# 🟦 **13. Comandos avanzados (muy útiles)**

### Ver YAML generado por Kubernetes
```
kubectl get deploy cine-platform -n cine -o yaml
```

### Ver logs de un pod anterior (si ha crasheado)
```
kubectl logs pod/<nombre> -n cine --previous
```

### Ver endpoints reales de un servicio
```
kubectl get endpoints pocketbase -n cine
```
