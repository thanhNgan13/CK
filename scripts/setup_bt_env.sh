#!/usr/bin/env bash
set -e

# ==========================
# Cấu hình
# ==========================
PYTHON_VERSION="3.10.11"
PROJECT_DIR="${1:-$PWD}"

echo ">>> Dự án: $PROJECT_DIR"
echo ">>> Python version sẽ dùng: $PYTHON_VERSION"
echo

# ==========================
# 1. Cài gói build cần thiết (Ubuntu/Debian/WSL)
# ==========================
if command -v apt-get >/dev/null 2>&1; then
    echo ">>> Phát hiện apt-get, cài đặt build dependencies cho pyenv..."
    sudo apt-get update
    sudo apt-get install -y \
        make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
        libffi-dev liblzma-dev git
else
    echo "!!! Không tìm thấy apt-get."
    echo "!!! Bạn đang dùng distro khác (Fedora/Arch/...). Hãy tự cài các gói build cho pyenv theo docs:"
    echo "    https://github.com/pyenv/pyenv/wiki#suggested-build-environment"
    echo
fi

# ==========================
# 2. Cài pyenv nếu chưa có
# ==========================
if [ ! -d "$HOME/.pyenv" ]; then
    echo ">>> Chưa có pyenv, tiến hành clone..."
    git clone https://github.com/pyenv/pyenv.git "$HOME/.pyenv"
else
    echo ">>> Đã có pyenv ở $HOME/.pyenv"
fi

# ==========================
# 3. Thiết lập pyenv cho shell hiện tại
# ==========================
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

if ! command -v pyenv >/dev/null 2>&1; then
    echo "!!! Không tìm thấy lệnh pyenv dù đã thêm PATH. Kiểm tra lại cài đặt."
    exit 1
fi

# init cho phiên shell hiện tại
eval "$(pyenv init -)"

# ==========================
# 4. Thêm cấu hình pyenv vào ~/.bashrc hoặc ~/.zshrc
# ==========================
SHELL_NAME="$(basename "$SHELL")"
RC_FILE=""

if [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
else
    RC_FILE="$HOME/.bashrc"
fi

if [ -n "$RC_FILE" ]; then
    if ! grep -q 'pyenv init' "$RC_FILE" 2>/dev/null; then
        echo ">>> Thêm cấu hình pyenv vào $RC_FILE"
        cat <<'EOF' >> "$RC_FILE"

# pyenv setup (tự động thêm bởi setup_bt_env.sh)
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
EOF
    else
        echo ">>> $RC_FILE đã có cấu hình pyenv, bỏ qua."
    fi
fi

# ==========================
# 5. Cài Python bằng pyenv
# ==========================
echo ">>> Cài Python $PYTHON_VERSION qua pyenv (nếu chưa có)..."
pyenv install -s "$PYTHON_VERSION"

# ==========================
# 6. Thiết lập environment cho dự án
# ==========================
echo ">>> Thiết lập môi trường trong thư mục dự án: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Gán local Python version cho project (tạo file .python-version)
pyenv local "$PYTHON_VERSION"

echo ">>> Python trong project:"
python --version

# Tạo venv .venv nếu chưa có
if [ ! -d ".venv" ]; then
    echo ">>> Tạo virtualenv .venv..."
    python -m venv .venv
else
    echo ">>> Đã có .venv, bỏ qua bước tạo."
fi

# Kích hoạt venv cho script
# shellcheck disable=SC1091
source .venv/bin/activate

echo ">>> Đang dùng Python trong venv:"
python --version

# Nâng cấp pip
python -m pip install --upgrade pip

# Cài requirements nếu có
if [ -f "requirements.txt" ]; then
    echo ">>> Cài đặt requirements.txt..."
    pip install -r requirements.txt
else
    echo ">>> Không tìm thấy requirements.txt trong $PROJECT_DIR, bỏ qua cài đặt package."
fi

echo
echo "==============================="
echo "Hoàn tất thiết lập môi trường!"
echo "Lần sau để làm việc với dự án:"
echo "  cd \"$PROJECT_DIR\""
echo "  pyenv local $PYTHON_VERSION"
echo "  source .venv/bin/activate"
echo "  python main.py   # hoặc lệnh bạn muốn chạy"
echo "==============================="
