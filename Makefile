# Voicemeeter Deck - Decky Plugin Makefile

# Configuration - update these for your setup
DECKIP ?= steamdeck
DECKUSER ?= deck
DECKPASS ?=
PLUGIN_NAME := voicemeeter-deck

# Paths
DECKDIR := /home/$(DECKUSER)/homebrew/plugins/$(PLUGIN_NAME)

.PHONY: all build clean deploy dev

all: build

# Install dependencies and build
build:
	npm install
	npm run build

# Clean build artifacts
clean:
	rm -rf dist node_modules

# Deploy to Steam Deck via SSH
# Requires SSH access configured
deploy: build
	ssh $(DECKUSER)@$(DECKIP) "mkdir -p $(DECKDIR)"
	scp -r dist/* $(DECKUSER)@$(DECKIP):$(DECKDIR)/
	scp -r backend/* $(DECKUSER)@$(DECKIP):$(DECKDIR)/
	scp plugin.json $(DECKUSER)@$(DECKIP):$(DECKDIR)/
	scp package.json $(DECKUSER)@$(DECKIP):$(DECKDIR)/
	@echo "Deployed! Restart Decky Loader to see changes."

# Deploy using rsync (faster for updates)
deploy-rsync: build
	rsync -avz --delete \
		dist/ \
		backend/ \
		plugin.json \
		package.json \
		defaults/ \
		$(DECKUSER)@$(DECKIP):$(DECKDIR)/
	@echo "Deployed! Restart Decky Loader to see changes."

# Watch mode for development
dev:
	npm run watch
