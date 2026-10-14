CLAUDE_SRC_DIR  := claude
AGENTS_SRC_DIR  := $(CLAUDE_SRC_DIR)/agents
AGENTS_DEST_DIR := $(HOME)/.claude/agents
SKILLS_SRC_DIR  := $(CLAUDE_SRC_DIR)/skills
SKILLS_DEST_DIR := $(HOME)/.claude/skills

AGENTS := $(wildcard $(AGENTS_SRC_DIR)/*.md)
SKILLS := $(wildcard $(SKILLS_SRC_DIR)/*)

COPILOT_SRC_DIR  := copilot
COPILOT_HOME     ?= $(HOME)/.copilot
COPILOT_BIN_DIR  ?= $(HOME)/.local/bin
COPILOT_AGENTS   := $(wildcard $(COPILOT_SRC_DIR)/agents/*.agent.md)
COPILOT_SKILLS   := $(wildcard $(COPILOT_SRC_DIR)/skills/*)
COPILOT_BINS     := $(wildcard $(COPILOT_SRC_DIR)/bin/*)

.PHONY: install uninstall reinstall list check copilot-install

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

copilot-install:
	@mkdir -p $(COPILOT_HOME)/agents $(COPILOT_HOME)/skills $(COPILOT_BIN_DIR)
	@for f in $(COPILOT_AGENTS); do \
		cp "$$f" $(COPILOT_HOME)/agents/; \
		echo "Installed agent: $(COPILOT_HOME)/agents/$$(basename $$f)"; \
	done
	@for s in $(COPILOT_SKILLS); do \
		rm -rf "$(COPILOT_HOME)/skills/$$(basename $$s)"; \
		cp -r "$$s" $(COPILOT_HOME)/skills/; \
		echo "Installed skill: $(COPILOT_HOME)/skills/$$(basename $$s)"; \
	done
	@for b in $(COPILOT_BINS); do \
		install -m 755 "$$b" $(COPILOT_BIN_DIR)/; \
		echo "Installed command: $(COPILOT_BIN_DIR)/$$(basename $$b)"; \
	done
	@rm -rf $(COPILOT_HOME)/hooks
	@cp -r $(COPILOT_SRC_DIR)/hooks $(COPILOT_HOME)/hooks
	@chmod 755 $(COPILOT_HOME)/hooks/scripts/*.py
	@echo "Installed hooks: $(COPILOT_HOME)/hooks"
	@cp $(COPILOT_SRC_DIR)/settings.json $(COPILOT_HOME)/settings.json
	@echo "Installed settings: $(COPILOT_HOME)/settings.json"
	@cp $(COPILOT_SRC_DIR)/copilot-instructions.md $(COPILOT_HOME)/copilot-instructions.md
	@echo "Installed instructions: $(COPILOT_HOME)/copilot-instructions.md"
	@if [ -e $(HOME)/.bash_copilot ]; then \
		echo "Kept autonomy settings: $(HOME)/.bash_copilot"; \
	else \
		cp $(COPILOT_SRC_DIR)/bash_copilot $(HOME)/.bash_copilot; \
		echo "Installed autonomy settings: $(HOME)/.bash_copilot"; \
	fi
	@command -v copilot >/dev/null 2>&1 \
		|| echo "WARNING: copilot CLI not found in PATH (files were installed anyway)."
	@case ":$$PATH:" in *":$(COPILOT_BIN_DIR):"*) ;; \
		*) echo "WARNING: $(COPILOT_BIN_DIR) is not in PATH; gutexberg will not be found." ;; esac
