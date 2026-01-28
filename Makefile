prepare:
	cd wrapped-video && npm run prepare-data -- $(file)

render:
	cd wrapped-video && npm run build

.PHONY: prepare render