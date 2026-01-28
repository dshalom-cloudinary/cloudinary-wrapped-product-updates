prepare:
	cd wrapped-video && npm run prepare-data -- $(params)

render:
	cd wrapped-video && npm run build

.PHONY: prepare render