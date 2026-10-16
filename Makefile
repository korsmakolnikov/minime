CLAUDE_SRC_DIR  := claude
AGENTS_SRC_DIR  := $(CLAUDE_SRC_DIR)/agents
AGENTS_DEST_DIR := $(HOME)/.claude/agents
SKILLS_SRC_DIR  := $(CLAUDE_SRC_DIR)/skills
SKILLS_DEST_DIR := $(HOME)/.claude/skills

HOOKS_SRC_DIR   := $(CLAUDE_SRC_DIR)/hooks
HOOKS_DEST_DIR  := $(HOME)/.claude/minime/hooks

AGENTS := $(wildcard $(AGENTS_SRC_DIR)/*.md)
SKILLS := $(wildcard $(SKILLS_SRC_DIR)/*)
CLAUDE_BINS := $(wildcard $(CLAUDE_SRC_DIR)/bin/*)

# Commands and signal schemas shared by the Copilot and the Claude Code
# workflows.
COMMON_SRC_DIR   := common
BIN_DIR          ?= $(HOME)/.local/bin
SIGNALS_DIR      ?= $(HOME)/.local/share/minime/signals
COMMON_BINS      := $(wildcard $(COMMON_SRC_DIR)/bin/*)
COMMON_SKILLS    := $(wildcard $(COMMON_SRC_DIR)/skills/*)

COPILOT_SRC_DIR  := copilot
COPILOT_HOME     ?= $(HOME)/.copilot
COPILOT_BIN_DIR  ?= $(BIN_DIR)
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

# Every file and folder the install targets copy into the system, for both
# CLIs, with the names they had before a rename, so that clean also removes
# what a rename left behind. Keep it updated: add an entry when an agent,
# skill, command, hook or setting file is added, and keep the old one when it
# is renamed or removed. `make clean-check` lists what the repository installs
# and this list misses. ~/.bash_copilot is left out on purpose: it holds the
# user's autonomy settings, and copilot-install never overwrites it.
INSTALLED := \
	$(AGENTS_DEST_DIR)/unclebob.md \
	$(SKILLS_DEST_DIR)/adl-fitness \
	$(SKILLS_DEST_DIR)/adl-interview \
	$(SKILLS_DEST_DIR)/adl-reverse \
	$(SKILLS_DEST_DIR)/adl-scaffold \
	$(SKILLS_DEST_DIR)/adl-spec \
	$(SKILLS_DEST_DIR)/domain-spec \
	$(SKILLS_DEST_DIR)/elixir-handbook \
	$(SKILLS_DEST_DIR)/elixir-style \
	$(SKILLS_DEST_DIR)/elixir-static-checks \
	$(SKILLS_DEST_DIR)/scaffold \
	$(HOME)/.claude/minime \
	$(BIN_DIR)/unclebob \
	$(BIN_DIR)/linus \
	$(BIN_DIR)/spec-check \
	$(BIN_DIR)/signal-check \
	$(SIGNALS_DIR) \
	$(COPILOT_HOME)/agents/argyris.agent.md \
	$(COPILOT_HOME)/agents/ford.agent.md \
	$(COPILOT_HOME)/agents/hughes.agent.md \
	$(COPILOT_HOME)/agents/joshua.agent.md \
	$(COPILOT_HOME)/agents/kent.agent.md \
	$(COPILOT_HOME)/agents/linus.agent.md \
	$(COPILOT_HOME)/agents/martin.agent.md \
	$(COPILOT_HOME)/agents/simon.agent.md \
	$(COPILOT_HOME)/agents/unclebob.agent.md \
	$(COPILOT_HOME)/agents/mortimer.agent.md \
	$(COPILOT_HOME)/agents/sherlock.agent.md \
	$(COPILOT_HOME)/agents/gutexberg.agent.md \
	$(COPILOT_HOME)/agents/soong.agent.md \
	$(COPILOT_HOME)/skills/adl-fitness \
	$(COPILOT_HOME)/skills/adl-interview \
	$(COPILOT_HOME)/skills/adl-reverse \
	$(COPILOT_HOME)/skills/adl-scaffold \
	$(COPILOT_HOME)/skills/adl-spec \
	$(COPILOT_HOME)/skills/domain-spec \
	$(COPILOT_HOME)/skills/elixir-handbook \
	$(COPILOT_HOME)/skills/elixir-style \
	$(COPILOT_HOME)/skills/elixir-static-checks \
	$(COPILOT_HOME)/skills/minime-sync \
	$(COPILOT_HOME)/skills/datadog-experiment-downloader \
	$(COPILOT_HOME)/hooks \
	$(COPILOT_HOME)/settings.json \
	$(COPILOT_HOME)/copilot-instructions.md \
	$(COPILOT_BIN_DIR)/kent \
	$(COPILOT_BIN_DIR)/argyris \
	$(COPILOT_BIN_DIR)/gutexberg \
	$(COPILOT_BIN_DIR)/mortimer

.PHONY: install install-copilot uninstall reinstall list check common-install copilot-install update clean clean-check

install: check common-install
	@mkdir -p $(AGENTS_DEST_DIR) $(SKILLS_DEST_DIR) $(HOOKS_DEST_DIR) $(BIN_DIR)
	@for f in $(AGENTS); do \
		cp "$$f" $(AGENTS_DEST_DIR)/; \
		echo "Installed agent: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done
	@for s in $(COMMON_SKILLS) $(SKILLS); do \
		rm -rf "$(SKILLS_DEST_DIR)/$$(basename $$s)"; \
		cp -r "$$s" $(SKILLS_DEST_DIR)/; \
		echo "Installed skill: $(SKILLS_DEST_DIR)/$$(basename $$s)"; \
	done
	@rm -rf $(HOOKS_DEST_DIR)
	@mkdir -p $(HOOKS_DEST_DIR)
	@install -m 755 $(HOOKS_SRC_DIR)/*.py $(HOOKS_DEST_DIR)/
	@echo "Installed hooks: $(HOOKS_DEST_DIR)"
	@for b in $(CLAUDE_BINS); do \
		install -m 755 "$$b" $(BIN_DIR)/; \
		echo "Installed command: $(BIN_DIR)/$$(basename $$b)"; \
	done

uninstall:
	@for f in $(AGENTS); do \
		rm -f $(AGENTS_DEST_DIR)/$$(basename $$f); \
		echo "Removed agent: $(AGENTS_DEST_DIR)/$$(basename $$f)"; \
	done
	@for s in $(COMMON_SKILLS) $(SKILLS); do \
		rm -rf "$(SKILLS_DEST_DIR)/$$(basename $$s)"; \
		echo "Removed skill: $(SKILLS_DEST_DIR)/$$(basename $$s)"; \
	done
	@rm -rf $(HOOKS_DEST_DIR)
	@echo "Removed hooks: $(HOOKS_DEST_DIR)"
	@for b in $(CLAUDE_BINS); do \
		rm -f $(BIN_DIR)/$$(basename $$b); \
		echo "Removed command: $(BIN_DIR)/$$(basename $$b)"; \
	done

reinstall: uninstall install

install-copilot: copilot-install

# Removes everything in INSTALLED; a path that does not exist is skipped.
clean:
	@for f in $(INSTALLED); do \
		if [ -e "$$f" ] || [ -L "$$f" ]; then rm -rf "$$f"; echo "Removed: $$f"; fi; \
	done
	@rmdir $(dir $(SIGNALS_DIR)) 2>/dev/null || true

# Lists what the repository installs and INSTALLED misses; fails if anything.
clean-check:
	@missing=0; \
	for p in $(foreach f,$(AGENTS),$(AGENTS_DEST_DIR)/$(notdir $(f))) \
		$(foreach s,$(COMMON_SKILLS) $(SKILLS),$(SKILLS_DEST_DIR)/$(notdir $(s))) \
		$(foreach b,$(CLAUDE_BINS) $(COMMON_BINS),$(BIN_DIR)/$(notdir $(b))) \
		$(foreach f,$(COPILOT_AGENTS),$(COPILOT_HOME)/agents/$(notdir $(f))) \
		$(foreach s,$(COMMON_SKILLS) $(COPILOT_SKILLS),$(COPILOT_HOME)/skills/$(notdir $(s))) \
		$(foreach b,$(COPILOT_BINS),$(COPILOT_BIN_DIR)/$(notdir $(b))); do \
		case " $(INSTALLED) " in *" $$p "*) ;; *) echo "Missing from INSTALLED: $$p"; missing=1 ;; esac; \
	done; \
	[ $$missing -eq 0 ] && echo "INSTALLED covers everything the repository installs."; \
	exit $$missing

list:
	@echo "Agents:"; ls -1 $(AGENTS_DEST_DIR) 2>/dev/null || echo "  none installed in $(AGENTS_DEST_DIR)."
	@echo "Skills:"; ls -1 $(SKILLS_DEST_DIR) 2>/dev/null || echo "  none installed in $(SKILLS_DEST_DIR)."

check:
	@command -v claude >/dev/null 2>&1 \
		&& echo "claude CLI found: $$(command -v claude)" \
		|| echo "WARNING: claude CLI not found in PATH (file installation proceeds anyway)."

common-install:
	@mkdir -p $(BIN_DIR) $(SIGNALS_DIR)
	@for b in $(COMMON_BINS); do \
		install -m 755 "$$b" $(BIN_DIR)/; \
		echo "Installed command: $(BIN_DIR)/$$(basename $$b)"; \
	done
	@rm -f $(SIGNALS_DIR)/*.schema.json
	@cp $(COMMON_SRC_DIR)/signals/*.schema.json $(SIGNALS_DIR)/
	@echo "Installed signal schemas: $(SIGNALS_DIR)"
	@case ":$$PATH:" in *":$(BIN_DIR):"*) ;; \
		*) echo "WARNING: $(BIN_DIR) is not in PATH; linus will not be found." ;; esac

copilot-install: common-install
	@mkdir -p $(COPILOT_HOME)/agents $(COPILOT_HOME)/skills $(COPILOT_BIN_DIR)
	@for f in $(COPILOT_AGENTS); do \
		cp "$$f" $(COPILOT_HOME)/agents/; \
		echo "Installed agent: $(COPILOT_HOME)/agents/$$(basename $$f)"; \
	done
	@for s in $(COMMON_SKILLS) $(COPILOT_SKILLS); do \
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
