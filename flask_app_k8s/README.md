# Sample flask app

Based on [docker/labs/flask-app](https://github.com/docker/labs/tree/bd6bcaa1e25e75dc3611ea063b3d38c65e205141/beginner/flask-app)

Added some type of config file to play with Kubernetes ConfigMaps

## Working with Docker Images

Build the image
```
export DOCKER_REPO=<docker-hub-user>
docker build -t $DOCKER_REPO/flask_app:1.0 .
```

- `-t` is the tag we give the image, this is used for running containers from the image.
  the tag assigned to an image is also used to identify the registry and repository to push and pull
  the data to and from.

  tags are made from:

  - `registry/` name - if left empty, this default to the Docker Hub
  - `repository/` name
  - `image:version` tag

Run a container from the Docker Image
```
docker run -d --name money_machine -p 5000:5000 $DOCKER_REPO/flask_app:1.0
open http://localhost:5000
```

- `-d` is to detach the terminal from the container process (run it in the background)
- `--name` is to specify a name for the container
- `-p local:container` is to forward traffic from a local port to a port in the container

Use `docker exec` to run a process in a container
```
docker exec -it money_machine sh
```

Verify container logs with `docker logs`
```
docker logs money_machine
```

Stop and remove the local container
```
docker stop money_machine && docker rm money_machine
```

To prepare deployment, Push the Docker image to a registry.

Make sure to provide log in credentials to your docker host first:

```
docker login <registry>
```

Where the image will be pushed, depends on your `$DOCKER_REPO` value:
```
docker push $DOCKER_REPO/flask_app:1.0
```

## Deploying to Kubernetes

We will first explore an imperative way of deploying our application on Kubernetes.

After this, we will learn how to manage and save our Deployment to facilitate collaboration on the deployment with others.

Before this, we have to ensure Kubernetes can pull our application image if our docker image is privately hosted.

### Pulling Images from a private registry

To pull from a private registry, Kubernetes will need the registry credentials.

First, use `kubectl` to create a secret of type `docker-registry` with your credentials:
```
kubectl create secret docker-registry honestbee-registry --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-pword> --docker-email=<your-email>
```

Above, we created a secret named `honestbee-registry`. We will need to tell Kubernetes to use this secret while pulling images.

imagePullSecrets can be defined per `Deployment` or alternatively the secret can be [added as an imagePullSecret to the default service account](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#adding-imagepullsecrets-to-a-service-account)

Service accounts are used by Pod resources to complete their tasks. A default Service account called `default` is made available
in every namespace by the Service Account Controller.

To update the default service account, ensure you have [`jq`](https://stedolan.github.io/jq) installed.

Run following command:
```
kubectl get serviceaccounts default -o json |
     jq  'del(.metadata.resourceVersion)'|
     jq 'setpath(["imagePullSecrets"];[{"name":"honestbee-registry"}])' |
     kubectl replace serviceaccount default -f -
```
Note: The `metadata.resourceVersion` field is used by the API server for optimistic concurrency. We are removing the `resourceVersion` and adding the `imagePullSecret` in the above oneliner. We are also replacing the default serviceaccount
with the modified json object streamed through stdin (`-`)

### Creating the Kubernetes deployment

Imperatively create a Kubernetes Deployment for the application by supplying:

- Name of the deployment
- Docker image used for the deployment
- Ports to be exposed on the Pods created by the deployment

```bash
kubectl run app --image=$DOCKER_REPO/flask_app:1.0 --port=5000
```

Inspect the Resources created by the above command using the Kubernetes UI.
To securely access the Kubernetes UI, use `kubectl` to create a proxy from your laptop to the Cluster.

```
kubectl proxy &
open http://localhost:8001/ui
```
**Note**: Following resources are of interest and can be drilled down from top to bottom:
- Deployment (notice the labels attached)
- ReplicaSet
- Pod (notice the ability to see the logs)

Use a label query to find all pods created by this Deployment manifest
```
kubectl get pods -l run=app
```

Use `kubectl logs` to get container logs in the Pod created by the deployment using the console:
```
POD_NAME=`kubectl get pods -l run=app -o name | head -n 1`
kubectl logs $POD_NAME -c app
```

Use `kubectl exec` to run a process (i.e. a shell) in a container of a Pod
```bash
kubectl exec -it ${POD_NAME#*/} -c app -- sh
```
**Note**: The bash variable expansion `{VAR#<pattern>} will strip the `<pattern>` from the env var

Use `kubectl port-forward` to forward traffic from a local port to a port in the container
```
kubectl port-forward ${POD_NAME#*/} 5000 &
open http://localhost:5000
```
**NOTE**: Once done, kill the port forwarding proxy as follows
```bash
# list all background jobs
jobs -l
# kill the job running the port forward %<job_nr>
kill -INT %1
```

Get the Deployment Manifest generated by the imperative command above:
```bash
kubectl get deploy app -o yaml > kubernetes/deploy-app-status.yaml
```

This Manifest is the declarative definition of the Deployment resource which will be managed by the Kubernetes Controllers.

After removing all status information and reducing it to the minimal keys required, our simplified Deployment Manifest looks as follows:
```bash
less kubernetes/deploy-app-simple.yaml
```
**Note**:
- `run` label created by the `kubectl run` command was replaced by a more commonly used `app` label
- container name was changed to `gunicorn` to reflect the main process of the container

To understand more about each key in the Deployment Manifest,
use `kubectl explain`:
```bash
kubectl explain deployment.spec.template.spec
```
In this case, the `spec.template.spec` is the `podSpec` used by ReplicaSets when creating Pods.

Delete the imperatively created Deployment with `kubectl delete deploy`:
```bash
kubectl delete deploy app
```

Use the manifest file to declaratively create the Deployment:
```bash
kubectl create -f kubernetes/deploy-app-simple.yaml
```

Use `kubectl logs` to get container logs in the Pod created by the deployment using the console:
```bash
POD_NAME=`kubectl get pods -l app=app -o name | head -n 1`
kubectl logs $POD_NAME -c gunicorn
```

## Working with ConfigMaps

Get a list of images from an imgur album (see [imgur](imgur/) folder for more info about the script)
```bash
docker build -t imgur_script imgur/
docker run -it --rm \
  -e "IMGUR_ALBUM_ID=R6xcQ" \
  -e "IMGUR_CLIENT_ID=88da..." \
  -e "IMGUR_CLIENT_SECRET=41d6..." \
  imgur_script > config/funnier-images.txt
```

Verify contents of `config/funnier-images.txt`
```bash
less config/funnier-images.txt
```

Configuration should be provided by the environment and not embedded within the Docker image.

In Kubernetes we use a `ConfigMap` resource to store one or multiple configuration files.

Create a Kubernetes ConfigMap from a local file using `kubectl create configmap`
```bash
kubectl create cm app-images --from-file=images.txt=config/funnier-images.txt
```

Inspect the generated ConfigMap manifest
```bash
kubectl get cm app-images -o yaml
```

Extract the data from the ConfigMap
```
kubectl get cm app-images -o jsonpath="{.data['images\.txt']}"
```

To use the ConfigMap define a volume in the PodSpec and mount the volume in the Container
```bash
less kubernetes/deploy-app-configmap.yaml
```

Apply these changes to our app Deployment
```bash
kubectl apply -f kubernetes/deploy-app-configmap.yaml
```

Confirm the Deployment is managing a controlled update for the new PodSpec by creating new Pods
```bash
kubectl get pods -w
```

Confirm the new images are mounted in the newly created Pod
```bash
POD_NAME=`kubectl get pods -l app=app -o name | head -n 1`
kubectl exec -t ${POD_NAME#*/} -c gunicorn -- cat /usr/src/app/config/images.txt
```

Test webservice
```bash
kubectl port-forward ${POD_NAME#*/} 5000 &
```

## Exposing the Deployment through a Service Resource

Imperatively create a Service resource for the app Deployment
```bash
kubectl expose deploy app --target-port=5000 --type=LoadBalancer
```

Get info about the exposed service
```bash
kubectl describe svc app
```

On Cloud providers, you will notice the external IP being provisioned
```bash
kubectl get svc -w
```

With minikube, use `minikube service` command to access the app through the service.
```
minikube service app
```
