# Slack Wrapped - Makefile

# Generate wrapped video from Slack data
generate:
	python -m slack_wrapped generate --data $(data) --config $(config) --output $(output)

# Validate input data and config
validate:
	python -m slack_wrapped validate --data $(data) --config $(config)

# Preview video in Remotion Studio
preview:
	python -m slack_wrapped preview --data $(data) --config $(config)
	cd wrapped-video && npm start

# Prepare video data for rendering
prepare:
	cd wrapped-video && npm run prepare-data -- $(file)

# Render the final video
render:
	cd wrapped-video && npm run build

# Full pipeline: generate, prepare, render
run:
	python -m slack_wrapped generate --data $(data) --config $(config) --output output
	cd wrapped-video && npm run prepare-data -- $$(ls -t ../output/video-data-*.json | head -1)
	cd wrapped-video && npm run build

# Install Python dependencies
install:
	pip install -r requirements.txt

# Install all dependencies (Python + Node.js)
install-all: install
	cd wrapped-video && npm install

# Run tests
test:
	python -m pytest tests/ -v

.PHONY: generate validate preview prepare render run install install-all test
