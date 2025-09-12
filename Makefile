PROJECT_NAME=deflakyzavr
export VERSION=$(shell cat deflakyzavr/version)

.PHONY: install-deps
install-deps:
	pip3 install --quiet --upgrade pip
	pip3 install --quiet -r requirements.txt

.PHONY: install-local
install-local: install-deps
	pip3 install . --force-reinstall

.PHONY: build
build:
	pip3 install --quiet --upgrade pip
	pip3 install --quiet --upgrade setuptools wheel twine
	python3 setup.py sdist bdist_wheel

.PHONY: publish
publish:
	twine upload dist/*

.PHONY: tag
tag:
	git tag v`cat ${PROJECT_NAME}/version`

.PHONY: build-image
build-image:
	docker build -f docker/Dockerfile . -t legionus18z/deflakyzavr:${VERSION}

.PHONY: push-image
push-image:
	docker push legionus18z/deflakyzavr:${VERSION}

.PHONY: buildx-build-n-push-image
buildx-build-n-push-image:
	docker buildx build --platform linux/amd64,linux/arm64 -f docker/Dockerfile . -t legionus18z/deflakyzavr:${VERSION} --push

.PHONY: buildx-builder
buildx-builder:
	docker buildx ls
	docker buildx create --driver docker-container --name deflakyzavr-builder || true
	docker buildx use --builder deflakyzavr-builder

