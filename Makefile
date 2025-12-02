build:
	@echo "Building..." && ./build.sh && echo "Build complete!"

lint:
	@ruff check .
