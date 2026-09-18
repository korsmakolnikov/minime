# {{PROJECT_NAME}} — thin wrapper around CMake.
#
#   make          build the executable (default)
#   make test     build and run the unit tests (Unity, via CTest)
#   make run      build and run the executable
#   make deps     install the toolchain (Ubuntu/Debian via apt, Arch via pacman)
#   make clean    remove the build directory
#
# Overridable variables (e.g. `make C_STANDARD=17 BUILD_TYPE=Release`):
#   C_STANDARD   C standard passed to CMake (11, 17, 23, ...)
#   TARGET_ARCH  target architecture (x86_64, i686, aarch64, ...)
#   BUILD_TYPE   CMake build type (Debug, Release, RelWithDebInfo, MinSizeRel)
#   BUILD_DIR    CMake build directory
#   CMAKE_FLAGS  extra flags forwarded to the CMake configure step

PROJECT     := {{PROJECT_NAME}}
TEST_BIN    := test_{{PROJECT_IDENT}}
BUILD_DIR   ?= build
BUILD_TYPE  ?= Debug
C_STANDARD  ?= {{C_STANDARD}}
TARGET_ARCH ?= {{TARGET_ARCH}}
CMAKE_FLAGS ?=

SUDO := $(shell [ "$$(id -u)" -eq 0 ] || echo sudo)

.PHONY: all build configure test run clean deps

all: build

configure:
	cmake -S . -B $(BUILD_DIR) \
		-DCMAKE_BUILD_TYPE=$(BUILD_TYPE) \
		-DCMAKE_C_STANDARD=$(C_STANDARD) \
		-DTARGET_ARCH=$(TARGET_ARCH) \
		$(CMAKE_FLAGS)

build: configure
	cmake --build $(BUILD_DIR) --target $(PROJECT)

test: configure
	cmake --build $(BUILD_DIR) --target $(TEST_BIN)
	ctest --test-dir $(BUILD_DIR) --output-on-failure

run: build
	./$(BUILD_DIR)/$(PROJECT)

clean:
	rm -rf $(BUILD_DIR)

deps:
	@. /etc/os-release; \
	case "$$ID $${ID_LIKE:-}" in \
		*arch*) \
			$(SUDO) pacman -S --needed --noconfirm base-devel cmake git ;; \
		*ubuntu*|*debian*) \
			export DEBIAN_FRONTEND=noninteractive; \
			$(SUDO) apt-get update && \
			$(SUDO) apt-get install -y --no-install-recommends build-essential cmake git ca-certificates ;; \
		*) \
			echo "Unsupported distribution: $$ID. Install gcc, make, cmake and git manually." >&2; exit 1 ;; \
	esac
