-include .env.prod
export

AWS_REGION     ?= us-east-1
AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text)
ECR_BASE       := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) \
	  | docker login --username AWS --password-stdin $(ECR_BASE)

build-backend:
	docker build -f docker/backend.prod.Dockerfile -t budget-analyzer/backend:latest .

push: ecr-login
	docker tag budget-analyzer/backend:latest $(ECR_BASE)/budget-analyzer/backend:latest
	docker push $(ECR_BASE)/budget-analyzer/backend:latest

build-frontend:
	docker run --rm \
	  -v $(shell pwd)/frontend:/app \
	  -w /app \
	  -e VITE_API_URL=$(VITE_API_URL) \
	  node:20-alpine \
	  sh -c "npm install && npm run build"

deploy-frontend:
	aws s3 sync frontend/dist s3://$(S3_BUCKET) --delete

deploy-backend: push
	ssh -i $(EC2_KEY) ec2-user@$(EC2_HOST) \
	  "aws ecr get-login-password --region $(AWS_REGION) \
	    | docker login --username AWS --password-stdin $(ECR_BASE) \
	  && docker-compose -f docker-compose.prod.yml pull backend celery_worker \
	  && docker-compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate backend celery_worker"

deploy: build-backend deploy-backend build-frontend deploy-frontend
