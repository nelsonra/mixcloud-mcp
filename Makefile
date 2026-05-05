.PHONY: build-ui release-patch release-minor release-major publish

build-ui:
	cd mcp-app && npm run build
	git add src/mixcloud_mcp/static/mcp-app.html

release-patch: build-ui
	uvx bump-my-version bump patch

release-minor: build-ui
	uvx bump-my-version bump minor

release-major: build-ui
	uvx bump-my-version bump major

publish:
	uv build
	uv publish
