# 📘 PocketBase en Kubernetes (k3s) — Guía completa + Troubleshooting

Este documento resume todos los pasos necesarios para desplegar PocketBase en un clúster k3s (Jetson Nano/Orin) y recoge los problemas reales encontrados durante la instalación, junto con sus soluciones.

---

# 🚀 1. Despliegue de PocketBase en k3s

### **Deployment YAML**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pocketbase
  namespace: cine
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pocketbase
  template:
    metadata:
      labels:
        app: pocketbase
    spec:
      containers:
        - name: pocketbase
          image: ghcr.io/muchobien/pocketbase:latest
          args: ["serve", "--http=0.0.0.0:8070"]
          ports:
            - containerPort: 8070
          volumeMounts:
            - name: pb-data
              mountPath: /pb_data
      volumes:
        - name: pb-data
          persistentVolumeClaim:
            claimName: pocketbase-pvc
```

Aplicar:

```bash
kubectl apply -f k3s/pocketbase-deployment.yaml
```

Reiniciar el pod:

```bash
kubectl delete pod -n cine -l app=pocketbase --force --grace-period=0
```

---

# 🌐 2. Acceso a PocketBase

Port‑forward:

```bash
kubectl port-forward -n cine pod/<nombre-del-pod> 8070:8070
```

Abrir en navegador:

```
http://localhost:8070/_/
```

---

# 🔍 3. Problemas encontrados y soluciones

## ❗ Problema 1: `ImagePullBackOff` desde GHCR o Docker Hub

**Síntoma:**

```
failed to fetch anonymous token: 403 Forbidden
pull access denied
```

**Causa:**  
Jetson/k3s no puede descargar imágenes desde GHCR o Docker Hub (restricciones de red, ARM64, etc.).

**Solución:**  
Usar una imagen que ya esté descargada o que no requiera autenticación.  
En este caso, la imagen `ghcr.io/muchobien/pocketbase` ya estaba presente en el nodo.

---

## ❗ Problema 2: La UI muestra “Superuser login” pero el login falla siempre

**Síntoma:**

- Pantalla de login antigua  
- Error: *Invalid login credentials*  
- El superusuario existe pero no entra  
- El endpoint `/api/admins/auth-with-password` devuelve 404

**Causa real:**  
PocketBase estaba en **modo instalación pendiente**, pero la UI no redirigía automáticamente.

**Solución:**  
Mirar los logs del pod:

```bash
kubectl logs -n cine pod/<pocketbase-pod>
```

Y aparece:

```
Launch the URL below in the browser to create your first superuser:
http://0.0.0.0:8070/_/#/pbinstal/<token>
```

Abrir ese enlace → crear superusuario → PocketBase queda inicializado.

---

## ❗ Problema 3: `pocketbase superuser create` no funciona

**Síntoma:**

```
unknown flag: --email
```

**Causa:**  
La versión 0.36.2 usa comandos distintos.

**Solución correcta:**

```bash
pocketbase superuser upsert EMAIL PASSWORD
```

Ejemplo:

```bash
pocketbase superuser upsert felixmurcia@gmail.com 123456
```

---

## ❗ Problema 4: ¿Dónde está guardado el superusuario?

**Verificar directorio de datos:**

```bash
ls -la /pb_data
ls -la pb_data
```

Ambos deben ser idénticos (PVC montado correctamente).

---

## ❗ Problema 5: ¿Qué versión de PocketBase está corriendo?

```bash
pocketbase --version
```

Salida:

```
pocketbase version 0.36.2
```

---

## ❗ Problema 6: Confirmar qué binario ejecuta el servidor

```bash
ps aux | grep pocketbase
```

Salida:

```
/usr/local/bin/pocketbase serve --http=0.0.0.0:8070
```

---

# 🧪 4. Comprobación del login vía API

```bash
curl -X POST http://localhost:8070/api/admins/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{"identity":"EMAIL","password":"PASS"}'
```

Si devuelve 404 → PocketBase está en modo instalación → abrir URL `pbinstal`.

---

# 🎉 5. Conclusión

El despliegue de PocketBase en k3s funciona perfectamente, pero hay que tener en cuenta:

- Algunas imágenes no son coherentes o no descargan correctamente.  
- PocketBase puede quedar en **modo instalación** sin avisar en la UI.  
- El comando correcto para crear superusuarios es `upsert`.  
- Los logs del pod contienen la URL de instalación que desbloquea todo.  

Una vez completado el instalador (`pbinstal`), el login funciona sin problemas.

## Problemas Comunes y Soluciones

### 1. **No se puede acceder como superuser después de la instalación**

#### Síntoma:
- Error: "Invalid login credentials" en la UI
- Comando `pocketbase superuser create` no funciona
- El superuser parece creado pero no puede autenticarse

#### Solución:
**Usar `superuser upsert` en lugar de `superuser create` cuando la base de datos está vacía:**

```bash
# Acceder al pod
kubectl exec -n cine -it pod/pocketbase-[NOMBRE] -- sh

# COMANDO CORRECTO (funciona con DB vacía)
pocketbase superuser upsert email@ejemplo.com ContraseñaSegura

# COMANDO INCORRECTO (falla con DB vacía)
pocketbase superuser create email@ejemplo.com ContraseñaSegura
```

#### Explicación:
PocketBase necesita inicializar la estructura de la base de datos antes de crear superusers. `upsert` maneja esto automáticamente, mientras que `create` falla si las tablas no existen.

### 2. **Error al hacer port-forward del pod**

#### Síntoma:
```bash
Error from server (NotFound): pods "pocketbase-7755777d58-wnbtw" not found
```

#### Solución:
Verificar el nombre exacto del pod:

```bash
# Listar todos los pods en el namespace
kubectl get pods -n cine -o wide

# Usar el nombre correcto para port-forward
kubectl port-forward -n cine pod/pocketbase-[NOMBRE_CORRECTO] 8070:8070
```

### 3. **Comandos de superuser con sintaxis incorrecta**

#### Síntoma:
```bash
Error: unknown flag: --email
Error: unknown flag: --password
```

#### Solución:
La sintaxis correcta en PocketBase 0.36.2 es:

```bash
# Sintaxis CORRECTA
pocketbase superuser upsert EMAIL PASSWORD

# Sintaxis INCORRECTA
pocketbase superuser upsert --email EMAIL --password PASSWORD
```

### 4. **Error 404 al autenticar por API**

#### Síntoma:
```bash
curl -X POST http://localhost:8070/api/admins/auth-with-password
{"data":{},"message":"The requested resource wasn't found.","status":404}
```

#### Solución:
En versiones antiguas de PocketBase (como 0.36.2):
1. Los superusers solo pueden autenticarse por la UI web (`/_/`)
2. Para autenticación API, usa usuarios normales:

```bash
# Para usuarios normales (colección "users")
curl -X POST http://localhost:8070/api/collections/users/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{"identity":"usuario@normal.com","password":"password123"}'
```

### 5. **Error "Failed to authenticate"**

#### Síntoma:
```bash
{"data":{},"message":"Failed to authenticate.","status":400}
```

#### Causas y Soluciones:

**A. Credenciales incorrectas:**
```bash
# Resetear y crear de nuevo
kubectl exec -n [NAMESPACE] -it pod/[POD_NAME] -- rm /pb_data/data.db
kubectl exec -n [NAMESPACE] -it pod/[POD_NAME] -- pocketbase superuser upsert email@ejemplo.com NuevaContraseñaSimple
```

**B. Caracteres especiales en la contraseña:**
- Usar contraseñas sin caracteres especiales complejos
- Ejemplo: `Admin123456` en lugar de `P@ssw0rd!`

### 6. **Primera instalación - Enlace de instalación**

Cuando PocketBase se inicia por primera vez con una base de datos vacía, muestra en los logs:

```
(!) Launch the URL below in the browser to create your first superuser account:
http://0.0.0.0:8070/_/#/pbinstal/TOKEN_JWT_AQUI
```

#### Solución:
1. Hacer port-forward
2. Abrir el enlace COMPLETO en el navegador
3. O usar el comando alternativo del log:
   ```bash
   /usr/local/bin/pocketbase superuser upsert EMAIL PASS
   ```

### 7. **Verificar que PocketBase está funcionando**

#### Comandos de diagnóstico:

```bash
# 1. Verificar salud de la API
curl http://localhost:8070/api/health

# 2. Verificar UI está accesible
curl -v http://localhost:8070/_/

# 3. Verificar logs del pod
kubectl logs -n cine pod/pocketbase-[NOMBRE]

# 4. Verificar archivos de base de datos
kubectl exec -n cine -it pod/pocketbase-[NOMBRE] -- ls -la /pb_data/
```

### 8. **Flujo de solución completo para superuser**

```bash
# PASO 1: Eliminar base de datos existente
kubectl exec -n cine -it pod/pocketbase-[NOMBRE] -- rm -f /pb_data/data.db

# PASO 2: Esperar reinicio automático (10-15 segundos)
sleep 15

# PASO 3: Crear superuser con UPSERT
kubectl exec -n cine -it pod/pocketbase-[NOMBRE] -- \
  pocketbase superuser upsert admin@ejemplo.com ContraseñaSimple123

# PASO 4: Hacer port-forward
kubectl port-forward -n cine pod/pocketbase-[NOMBRE] 8070:8070

# PASO 5: Acceder por navegador
# URL: http://localhost:8070/_/
# Credenciales: admin@ejemplo.com / ContraseñaSimple123
```

### 9. **Problemas con volúmenes persistentes**

#### Síntoma:
Los superusers se pierden después de reiniciar el pod.

#### Solución:
Verificar la configuración del PersistentVolumeClaim:

```bash
# Verificar PVC
kubectl get pvc -n cine

# Verificar montaje en el pod
kubectl describe pod -n cine pocketbase-[NOMBRE]
```

### 10. **Comandos útiles de Kubernetes**

```bash
# Reiniciar deployment
kubectl rollout restart deployment -n cine pocketbase

# Verificar estado del deployment
kubectl get deployment -n cine pocketbase -o yaml

# Verificar eventos
kubectl get events -n cine --sort-by='.lastTimestamp'

# Acceder a shell del pod
kubectl exec -n cine -it pod/pocketbase-[NOMBRE] -- sh
```
### 11. Acceder a la interfaz de administración de PocketBase

Para acceder a la interfaz de administración de PocketBase, se debe hacer port-forward del pod de PocketBase al puerto 8070.
Ejecutar el comando para consultar los logs 

```bash
kubectl port-forward -n cine deploy/pocketbase 8070:8070
```

```bash
kubectl logs -n cine -l app=pocketbase
```

Ahi aparecerá la URL para acceder a la interfaz de administración de PocketBase.

Ejemplo:

```
2026/02/09 12:45:30 Server started at http://0.0.0.0:8070
├─ REST API:  http://0.0.0.0:8070/api/
└─ Dashboard: http://0.0.0.0:8070/_/

(!) Launch the URL below in the browser if it hasn't been open already to create your first superuser account:
http://0.0.0.0:8070/_/#/pbinstal/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjb2xsZWN0aW9uSWQiOiJwYmNfMzE0MjYzNTgyMyIsImV4cCI6MTc3MDY0MjkzMCwiaWQiOiJjbzA1N3BvYmdudWg3d2wiLCJyZWZyZXNoYWJsZSI6ZmFsc2UsInR5cGUiOiJhdXRoIn0.YyTtL5m8wGjO0kiGIx_Q5UkCE4EjL-E-7vM8f5VKBWg
(you can also create your first superuser by running: /usr/local/bin/pocketbase superuser upsert EMAIL PASS)
```

## Resumen de Buenas Prácticas

1. **Siempre usar `upsert`** en lugar de `create` para superusers
2. **Contraseñas simples** sin caracteres especiales complejos
3. **Verificar logs** después de cada operación
4. **Acceder primero por UI** para superusers, luego usar API para usuarios normales
5. **Resetear completamente** eliminando `data.db` si hay problemas persistentes

## Estructura de archivos esperada

```bash
/pb_data/
├── data.db          # Base de datos principal (SQLite)
├── auxiliary.db     # Base de datos auxiliar
└── types.d.ts       # Definiciones TypeScript
```

## Versión de PocketBase

Este troubleshooting es específico para **PocketBase 0.36.2**. Versiones más recientes pueden tener comandos diferentes.

---

**¿Problemas persistentes?** Verifica siempre:
1. Logs del pod: `kubectl logs -n cine pod/pocketbase-[NOMBRE]`
2. Estado del pod: `kubectl describe pod -n cine pocketbase-[NOMBRE]`
3. Configuración del deployment: `kubectl get deployment -n cine pocketbase -o yaml`