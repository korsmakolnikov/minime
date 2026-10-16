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

# One-off migration from the old agent names (mortimer, sherlock, gutexberg,
# soong) to kent, martin, linus and argyris, and from .adl/ to .sources/;
# drop it once every machine ran it.
OLD_AGENTS       := mortimer sherlock gutexberg soong
OLD_BINS         := gutexberg mortimer
PROJECTS_DIR     ?= $(HOME)/code
SHELL_RC_FILES   := $(wildcard $(HOME)/.bashrc $(HOME)/.bash_aliases $(HOME)/.bash_profile $(HOME)/.profile $(HOME)/.zshrc)

.PHONY: install uninstall reinstall list check copilot-install update

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
	@rm -rf $(COPILOT_HOME)/signals
	@cp -r $(COPILOT_SRC_DIR)/signals $(COPILOT_HOME)/signals
	@echo "Installed signal schemas: $(COPILOT_HOME)/signals"
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
		*) echo "WARNING: $(COPILOT_BIN_DIR) is not in PATH; linus will not be found." ;; esac

update:
	@for a in $(OLD_AGENTS); do \
		f="$(COPILOT_HOME)/agents/$$a.agent.md"; \
		if [ -e "$$f" ]; then rm -f "$$f"; echo "Removed old agent: $$f"; fi; \
	done
	@for b in $(OLD_BINS); do \
		f="$(COPILOT_BIN_DIR)/$$b"; \
		if [ -e "$$f" ]; then rm -f "$$f"; echo "Removed old command: $$f"; fi; \
	done
	@if [ -f $(HOME)/.bash_copilot ]; then \
		sed -i -e 's/gutexberg/linus/g; s/GUTEXBERG/LINUS/g; s/soong/argyris/g; s/SOONG/ARGYRIS/g' $(HOME)/.bash_copilot; \
		echo "Renamed the autonomy settings in $(HOME)/.bash_copilot"; \
		if ! grep -q '^export COPILOT_CONTAINERS=' $(HOME)/.bash_copilot; then \
			printf '%s\n' '#   COPILOT_CONTAINERS  containers where agents may run commands' 'export COPILOT_CONTAINERS="crash"' >> $(HOME)/.bash_copilot; \
			echo "Added COPILOT_CONTAINERS=\"crash\" to $(HOME)/.bash_copilot"; \
		fi; \
	fi
	@for g in $$(find $(PROJECTS_DIR) -maxdepth 4 -type d -path '*/.git/gutexberg' -prune 2>/dev/null); do \
		d="$${g%/gutexberg}"; \
		if [ -e "$$d/linus" ]; then \
			echo "WARNING: $$d has both gutexberg and linus phase logs: merge them by hand."; \
		else \
			mv "$$g" "$$d/linus"; rm -f "$$d/gutexberg.lock"; \
			echo "Moved the phase history: $$d/linus"; \
		fi; \
	done
	@for d in $$(find $(PROJECTS_DIR) -maxdepth 3 -type d -name .git 2>/dev/null); do \
		if git --git-dir="$$d" config --get-regexp '^gutexberg\.' >/dev/null 2>&1; then \
			git --git-dir="$$d" config --rename-section gutexberg linus; \
			echo "Renamed git config gutexberg.* to linus.* in $$d"; \
		fi; \
	done
	@if git config --global --get-regexp '^gutexberg\.' >/dev/null 2>&1; then \
		git config --global --rename-section gutexberg linus; \
		echo "Renamed global git config gutexberg.* to linus.*"; \
	fi
	@for a in $$(find $(PROJECTS_DIR) -maxdepth 3 -type d -name .adl -prune 2>/dev/null); do \
		if [ -e "$${a%/.adl}/.sources" ]; then \
			echo "WARNING: $${a%/.adl} has both .adl/ and .sources/: merge them by hand."; \
		else \
			mv "$$a" "$${a%/.adl}/.sources"; echo "Moved $$a to .sources/"; \
		fi; \
	done
	@ignore="$$(git config --global --path --get core.excludesFile || echo $${XDG_CONFIG_HOME:-$(HOME)/.config}/git/ignore)"; \
	if [ -f "$$ignore" ]; then \
		for e in .sources/ .documentation/; do \
			grep -qxF "$$e" "$$ignore" || { echo "$$e" >> "$$ignore"; echo "Added $$e to the global git ignore file $$ignore"; }; \
		done; \
	else \
		echo "WARNING: no global git ignore file ($$ignore): keep .sources/ and .documentation/ out of git by hand."; \
	fi
	@if [ -e /tmp/mortimer-partial-session-progress.md ] && [ ! -e /tmp/kent-partial-session-progress.md ]; then \
		mv /tmp/mortimer-partial-session-progress.md /tmp/kent-partial-session-progress.md; \
		echo "Moved the pending session progress to /tmp/kent-partial-session-progress.md"; \
	fi
	@for f in $(SHELL_RC_FILES); do \
		grep -nHwE 'mortimer|sherlock|gutexberg|soong|AUTONOMY_GUTEXBERG|AUTONOMY_SOONG|GUTEXBERG_[A-Z]+' "$$f" \
			| sed 's/^/WARNING: old name, update by hand: /'; \
	done; true
	@$(MAKE) --no-print-directory copilot-install
