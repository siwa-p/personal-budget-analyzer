-include .env.prod
export

AWS_REGION     ?= us-east-1
AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text)
ECR_BASE       := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) \
	  | docker login --username AWS --password-stdin $(ECR_BASE)

build-backend:
	docker buildx build --platform linux/arm64 \
	  -f docker/backend.prod.Dockerfile \
	  -t budget-analyzer/backend:latest \
	  --load .

push: ecr-login
	docker buildx build --platform linux/arm64 \
	  -f docker/backend.prod.Dockerfile \
	  -t $(ECR_BASE)/budget-analyzer/backend:latest \
	  --push .

build-frontend:
	docker buildx build \
	  -f docker/frontend.prod.Dockerfile \
	  --target dist \
	  --build-arg VITE_API_URL=$(VITE_API_URL) \
	  --build-arg VITE_COGNITO_USER_POOL_ID=$(VITE_COGNITO_USER_POOL_ID) \
	  --build-arg VITE_COGNITO_CLIENT_ID=$(VITE_COGNITO_CLIENT_ID) \
	  --output type=local,dest=frontend/dist \
	  .

deploy-frontend:
	aws s3 sync frontend/dist s3://$(S3_BUCKET) --delete

deploy-backend: push
	scp -i $(EC2_KEY) .env.prod ec2-user@$(EC2_HOST):/home/ec2-user/.env
	scp -i $(EC2_KEY) docker-compose.prod.yml ec2-user@$(EC2_HOST):/home/ec2-user/docker-compose.prod.yml
	scp -i $(EC2_KEY) backend/.env.prod ec2-user@$(EC2_HOST):/home/ec2-user/backend/.env.prod
	ssh -i $(EC2_KEY) ec2-user@$(EC2_HOST) \
	  "aws ecr get-login-password --region $(AWS_REGION) \
	    | docker login --username AWS --password-stdin $(ECR_BASE) \
	  && docker compose --env-file /home/ec2-user/.env -f docker-compose.prod.yml down --remove-orphans \
	  && docker image prune -af \
	  && docker compose --env-file /home/ec2-user/.env -f docker-compose.prod.yml pull backend \
	  && docker compose --env-file /home/ec2-user/.env -f docker-compose.prod.yml up -d backend"

setup-instance:
	ssh -i $(EC2_KEY) ec2-user@$(EC2_HOST) "\
	  sudo dnf install -y docker && \
	  sudo systemctl enable --now docker && \
	  sudo usermod -aG docker ec2-user && \
	  sudo mkdir -p /usr/local/lib/docker/cli-plugins && \
	  sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
	    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
	  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose"
	scp -i $(EC2_KEY) docker-compose.prod.yml ec2-user@$(EC2_HOST):~/
	ssh -i $(EC2_KEY) ec2-user@$(EC2_HOST) "mkdir -p ~/backend"
	scp -i $(EC2_KEY) backend/.env.prod ec2-user@$(EC2_HOST):~/backend/.env.prod

setup-ecr-lifecycle:
	aws ecr put-lifecycle-policy \
	  --repository-name budget-analyzer/backend \
	  --region $(AWS_REGION) \
	  --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"Keep last 3 images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":3},"action":{"type":"expire"}}]}'

setup-prune-cron:
	ssh -i $(EC2_KEY) ec2-user@$(EC2_HOST) \
	  "sudo dnf install -y cronie && sudo systemctl enable --now crond \
	  && (crontab -l 2>/dev/null | grep -q 'docker system prune' \
	    || (crontab -l 2>/dev/null; echo '0 2 * * 0 docker system prune -f >> /var/log/docker-prune.log 2>&1') | crontab -)"

deploy: build-backend deploy-backend build-frontend deploy-frontend
