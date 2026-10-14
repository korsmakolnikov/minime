CLAUDE_SRC_DIR  := claude
AGENTS_SRC_DIR  := $(CLAUDE_SRC_DIR)/agents
AGENTS_DEST_DIR := $(HOME)/.claude/agents
SKILLS_SRC_DIR  := $(CLAUDE_SRC_DIR)/skills
SKILLS_DEST_DIR := $(HOME)/.claude/skills

AGENTS := $(wildcard $(AGENTS_SRC_DIR)/*.md)
SKILLS := $(wildcard $(SKILLS_SRC_DIR)/*)

.PHONY: install uninstall reinstall list check

install: check
	@mkdir -p $(AGENTS_DEST_DIR) $(SKILLS_DEST_DIR)
	@for f in $(AGENTS); do \
		cp "$$f" $(AGENTS_DEST_DIR)/; \
		echo "Installed agent: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done
	@for s in $(SKILLS); do \
		rm -rf "$(SKILLS_DEST_DIR)/$$(basename $$s)"; \
		cp -r "$$s" $(SKILLS_DEST_DIR)/; \
		echo "Installed skill: $(SKILLS_DEST_DIR)/$$(basename $$s)"; \
	done

uninstall:
	@for f in $(AGENTS); do \
		rm -f $(AGENTS_DEST_DIR)/$$(basename $$f); \
		echo "Removed agent: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done
	@for s in $(SKILLS); do \
		rm -rf "$(SKILLS_DEST_DIR)/$$(basename $$s)"; \
		echo "Removed skill: $(SKILLS_DEST_DIR)/$$(basename $$s)"; \
	done

reinstall: uninstall install

list:
	@echo "Agents:"; ls -1 $(AGENTS_DEST_DIR) 2>/dev/null || echo "  none installed in $(AGENTS_DEST_DIR)."
	@echo "Skills:"; ls -1 $(SKILLS_DEST_DIR) 2>/dev/null || echo "  none installed in $(SKILLS_DEST_DIR)."

check:
	@command -v claude >/dev/null 2>&1 \
		&& echo "claude CLI found: $$(command -v claude)" \
		|| echo "WARNING: claude CLI not found in PATH (file installation proceeds anyway)."
