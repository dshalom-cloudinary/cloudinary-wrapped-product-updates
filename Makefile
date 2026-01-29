collect:
	python -m github_wrapped --github-username $(username)

prepare:
	cd wrapped-video && npm run prepare-data -- $(file)

render:
	cd wrapped-video && npm run build

run:
	python -m github_wrapped --github-username $(username)
	cd wrapped-video && npm run prepare-data -- $$(ls -t ../output/video-data-*.json | head -1)
	cd wrapped-video && npm run build

.PHONY: prepare render collect run