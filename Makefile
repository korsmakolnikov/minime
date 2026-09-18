AGENTS_SRC_DIR := agents
AGENTS_DEST_DIR := $(HOME)/.claude/agents

AGENTS := $(wildcard $(AGENTS_SRC_DIR)/*.md)

.PHONY: install uninstall reinstall list check

install: check
	@mkdir -p $(AGENTS_DEST_DIR)
	@for f in $(AGENTS); do \
		cp "$$f" $(AGENTS_DEST_DIR)/; \
		echo "Installed: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done

uninstall:
	@for f in $(AGENTS); do \
		rm -f $(AGENTS_DEST_DIR)/$$(basename $$f); \
		echo "Removed: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done

reinstall: uninstall install

list:
	@ls -1 $(AGENTS_DEST_DIR) 2>/dev/null || echo "No agents installed in $(AGENTS_DEST_DIR)."

check:
	@command -v claude >/dev/null 2>&1 \
		&& echo "claude CLI found: $$(command -v claude)" \
		|| echo "WARNING: claude CLI not found in PATH (file installation proceeds anyway)."
