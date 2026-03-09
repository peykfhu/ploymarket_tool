#!/bin/bash
# ============================================
# Polymarket 套利系统 - 一键部署
# 仓库: https://github.com/peykfhu/ploymarket_tool.git
#
# 用法: curl -fsSL https://raw.githubusercontent.com/peykfhu/ploymarket_tool/main/install.sh | bash
# ============================================

set -e

REPO_URL="https://github.com/peykfhu/ploymarket_tool.git"
BRANCH="main"
INSTALL_DIR="$HOME/ploymarket_tool"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}!${NC} $1"; }
log_err()  { echo -e "  ${RED}✗${NC} $1"; }
log_do()   { echo -e "  ${BLUE}→${NC} $1"; }

clear
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}║   🤖  Polymarket 套利系统 ${BOLD}一键部署${NC}${CYAN}                ║${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}║   github.com/peykfhu/ploymarket_tool              ║${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# 检测系统
# ============================================
detect_system() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        OS="unknown"
    fi

    if command -v apt-get &>/dev/null; then
        PKG="apt"
    elif command -v dnf &>/dev/null; then
        PKG="dnf"
    elif command -v yum &>/dev/null; then
        PKG="yum"
    elif command -v pacman &>/dev/null; then
        PKG="pacman"
    elif command -v apk &>/dev/null; then
        PKG="apk"
    else
        PKG="unknown"
    fi

    ARCH=$(uname -m)
    echo -e "${BOLD}系统信息${NC}"
    log_ok "系统: $OS | 包管理器: $PKG | 架构: $ARCH"
    echo ""
}

detect_system

# ============================================
# 1. 安装基础依赖
# ============================================
echo -e "${BOLD}[1/7] 安装基础依赖${NC}"

install_basics() {
    case $PKG in
        apt)
            sudo apt-get update -y -qq
            sudo apt-get install -y -qq curl wget git ca-certificates gnupg lsb-release net-tools > /dev/null 2>&1
            ;;
        dnf)
            sudo dnf install -y -q curl wget git ca-certificates net-tools > /dev/null 2>&1
            ;;
        yum)
            sudo yum install -y -q curl wget git ca-certificates net-tools > /dev/null 2>&1
            ;;
        pacman)
            sudo pacman -Sy --noconfirm --quiet curl wget git net-tools > /dev/null 2>&1
            ;;
        apk)
            sudo apk add --quiet curl wget git net-tools > /dev/null 2>&1
            ;;
        *)
            log_warn "未知包管理器，跳过基础依赖安装"
            ;;
    esac
    log_ok "基础工具 (curl, git, wget) 就绪"
}

install_basics

# ============================================
# 2. 安装 Docker
# ============================================
echo ""
echo -e "${BOLD}[2/7] 检查 Docker${NC}"

install_docker() {
    if command -v docker &>/dev/null; then
        DOCKER_VER=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1)
        log_ok "Docker 已安装 (v${DOCKER_VER})"
    else
        log_do "安装 Docker..."
        curl -fsSL https://get.docker.com | sudo sh > /dev/null 2>&1
        log_ok "Docker 安装完成"
    fi

    # 确保 Docker 运行中
    if ! sudo docker info &>/dev/null 2>&1; then
        sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
        sudo systemctl enable docker 2>/dev/null || true
    fi

    # 当前用户加入 docker 组
    sudo usermod -aG docker $USER 2>/dev/null || true
    log_ok "Docker 服务运行中"
}

install_docker

# ============================================
# 3. 安装 Docker Compose
# ============================================
echo ""
echo -e "${BOLD}[3/7] 检查 Docker Compose${NC}"

install_compose() {
    # V2 插件
    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_VER=$(docker compose version --short 2>/dev/null)
        log_ok "Docker Compose V2 已安装 (v${COMPOSE_VER})"
        COMPOSE_CMD="sudo docker compose"
        return
    fi

    # V1 独立
    if command -v docker-compose &>/dev/null; then
        log_ok "Docker Compose V1 已安装"
        COMPOSE_CMD="sudo docker-compose"
        return
    fi

    # 安装 V2
    log_do "安装 Docker Compose..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins

    case $ARCH in
        x86_64)  CARCH="x86_64" ;;
        aarch64) CARCH="aarch64" ;;
        armv7l)  CARCH="armv7" ;;
        *)       CARCH="x86_64" ;;
    esac

    sudo curl -fsSL \
        "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${CARCH}" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose 2>/dev/null
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    sudo ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true

    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="sudo docker compose"
        log_ok "Docker Compose V2 安装完成"
    else
        log_err "Docker Compose 安装失败"
        exit 1
    fi
}

install_compose

# 最终确认 compose 命令
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="sudo docker-compose"
fi

# ============================================
# 4. 拉取代码
# ============================================
echo ""
echo -e "${BOLD}[4/7] 拉取代码${NC}"

pull_code() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_do "更新已有代码..."
        cd "$INSTALL_DIR"
        git fetch origin 2>/dev/null
        git reset --hard origin/$BRANCH 2>/dev/null
        git pull origin $BRANCH 2>/dev/null
        log_ok "代码已更新到最新"
    else
        # 如果目录存在但不是 git 仓库，备份
        if [ -d "$INSTALL_DIR" ]; then
            mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%s)"
            log_warn "旧目录已备份"
        fi

        log_do "克隆仓库 peykfhu/ploymarket_tool..."
        git clone -b $BRANCH "$REPO_URL" "$INSTALL_DIR" 2>/dev/null
        log_ok "代码克隆完成"
    fi

    cd "$INSTALL_DIR"
}

pull_code

# ============================================
# 5. 配置环境 + 补全文件
# ============================================
echo ""
echo -e "${BOLD}[5/7] 配置环境${NC}"

setup_environment() {
    cd "$INSTALL_DIR"

    # 创建必要目录
    mkdir -p data logs backend/agents backend/services backend/utils
    mkdir -p frontend/src/components frontend/src/hooks frontend/public

    # 确保 Python __init__.py 存在
    touch backend/agents/__init__.py 2>/dev/null
    touch backend/services/__init__.py 2>/dev/null
    touch backend/utils/__init__.py 2>/dev/null
    touch frontend/public/favicon.ico 2>/dev/null

    # 确保 logs 目录存在（后端需要）
    mkdir -p backend/logs

    log_ok "目录结构完整"

    # 处理 .env
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_ok "已从 .env.example 创建 .env"
        else
            cat > .env << 'ENVFILE'
# Polymarket 套利系统配置
# ============================================

# 端口（避开 3000 和 8000）
BACKEND_PORT=8899
FRONTEND_PORT=3999
WS_PORT=8898

# Polymarket API
POLYMARKET_API_KEY=
POLYMARKET_API_SECRET=
POLYMARKET_WALLET_ADDRESS=
POLYMARKET_PRIVATE_KEY=

# NOAA 天气 API（免费）
NOAA_API_TOKEN=

# Binance API（只需读取权限）
BINANCE_API_KEY=
BINANCE_API_SECRET=

# 新闻 API
NEWSAPI_KEY=

# 通知（可选）
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

# 风控
MAX_POSITION_SIZE=50
MAX_DAILY_LOSS=200
MIN_EDGE_THRESHOLD=0.08
MAX_CONCURRENT_POSITIONS=20
STOP_LOSS_PERCENT=0.15

# 数据库
DATABASE_URL=sqlite:///./polymarket_bot.db

# 安全
DASHBOARD_PASSWORD=admin123
JWT_SECRET=change-me-please

# 模式：true = 模拟交易（不会真正下单）
DRY_RUN=true
LOG_LEVEL=INFO
ENVFILE
            log_ok "已创建默认 .env"
        fi

        echo ""
        echo -e "  ${YELLOW}┌─────────────────────────────────────────┐${NC}"
        echo -e "  ${YELLOW}│  ⚠️  需要配置 API Keys                  │${NC}"
        echo -e "  ${YELLOW}│                                         │${NC}"
        echo -e "  ${YELLOW}│  编辑: nano $INSTALL_DIR/.env   │${NC}"
        echo -e "  ${YELLOW}│                                         │${NC}"
        echo -e "  ${YELLOW}│  必填:                                  │${NC}"
        echo -e "  ${YELLOW}│    POLYMARKET_API_KEY                   │${NC}"
        echo -e "  ${YELLOW}│    POLYMARKET_API_SECRET                │${NC}"
        echo -e "  ${YELLOW}│                                         │${NC}"
        echo -e "  ${YELLOW}│  推荐:                                  │${NC}"
        echo -e "  ${YELLOW}│    NOAA_API_TOKEN (天气Agent)           │${NC}"
        echo -e "  ${YELLOW}│    BINANCE_API_KEY (加密货币Agent)      │${NC}"
        echo -e "  ${YELLOW}│    NEWSAPI_KEY (新闻Agent)              │${NC}"
        echo -e "  ${YELLOW}│                                         │${NC}"
        echo -e "  ${YELLOW}│  当前: DRY_RUN=true (模拟模式)          │${NC}"
        echo -e "  ${YELLOW}└─────────────────────────────────────────┘${NC}"
        echo ""

        read -p "$(echo -e "  ${CYAN}现在编辑 .env 配置 API？[Y/n]:${NC} ")" EDIT_CHOICE
        EDIT_CHOICE=${EDIT_CHOICE:-Y}
        if [[ "$EDIT_CHOICE" =~ ^[Yy] ]]; then
            if command -v nano &>/dev/null; then
                nano "$INSTALL_DIR/.env"
            elif command -v vi &>/dev/null; then
                vi "$INSTALL_DIR/.env"
            fi
        else
            log_warn "稍后记得编辑 .env 配置 API Keys"
        fi
    else
        log_ok ".env 已存在，保留现有配置"
    fi
}

setup_environment

# ============================================
# 6. 防火墙
# ============================================
echo ""
echo -e "${BOLD}[6/7] 配置防火墙${NC}"

setup_firewall() {
    # 从 .env 读端口
    F_PORT=$(grep -E "^FRONTEND_PORT=" .env 2>/dev/null | cut -d= -f2)
    B_PORT=$(grep -E "^BACKEND_PORT=" .env 2>/dev/null | cut -d= -f2)
    F_PORT=${F_PORT:-3999}
    B_PORT=${B_PORT:-8899}

    OPENED=false

    # ufw
    if command -v ufw &>/dev/null && sudo ufw status 2>/dev/null | grep -q "active"; then
        sudo ufw allow $F_PORT/tcp &>/dev/null || true
        sudo ufw allow $B_PORT/tcp &>/dev/null || true
        OPENED=true
        log_ok "ufw: 开放端口 $F_PORT, $B_PORT"
    fi

    # firewalld
    if command -v firewall-cmd &>/dev/null && sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
        sudo firewall-cmd --permanent --add-port=${F_PORT}/tcp &>/dev/null || true
        sudo firewall-cmd --permanent --add-port=${B_PORT}/tcp &>/dev/null || true
        sudo firewall-cmd --reload &>/dev/null || true
        OPENED=true
        log_ok "firewalld: 开放端口 $F_PORT, $B_PORT"
    fi

    if [ "$OPENED" = false ]; then
        log_ok "未检测到活跃防火墙，跳过"
    fi

    # 云服务器安全组提醒
    echo -e "  ${YELLOW}!${NC} 如果是云服务器，记得在安全组开放端口 ${BOLD}$F_PORT${NC} 和 ${BOLD}$B_PORT${NC}"
}

setup_firewall

# ============================================
# 7. 构建并启动
# ============================================
echo ""
echo -e "${BOLD}[7/7] 构建并启动服务${NC}"

build_and_start() {
    cd "$INSTALL_DIR"

    # 停止旧容器
    $COMPOSE_CMD down 2>/dev/null || true

    # 构建
    log_do "构建 Docker 镜像（首次可能需要 3-5 分钟）..."
    echo ""
    $COMPOSE_CMD build 2>&1 | while IFS= read -r line; do
        # 只显示关键进度
        if echo "$line" | grep -qE "^(Step|Successfully|Building|DONE|\-\-\->)"; then
            echo -e "    ${BLUE}│${NC} $line"
        fi
    done

    echo ""
    log_ok "镜像构建完成"

    # 启动
    log_do "启动容器..."
    $COMPOSE_CMD up -d

    echo ""
    log_do "等待服务就绪..."

    # 等待后端启动
    B_PORT=$(grep -E "^BACKEND_PORT=" .env 2>/dev/null | cut -d= -f2)
    B_PORT=${B_PORT:-8899}

    READY=false
    for i in $(seq 1 20); do
        if curl -sf "http://localhost:${B_PORT}/api/health" &>/dev/null; then
            READY=true
            break
        fi
        sleep 2
        echo -ne "    等待中... ${i}s\r"
    done

    echo ""
    if [ "$READY" = true ]; then
        log_ok "后端服务 ✓ 运行正常"
    else
        log_warn "后端还在启动，查看日志: sudo docker logs -f polymarket-backend"
    fi

    # 检查前端
    F_PORT=$(grep -E "^FRONTEND_PORT=" .env 2>/dev/null | cut -d= -f2)
    F_PORT=${F_PORT:-3999}

    if curl -sf "http://localhost:${F_PORT}" &>/dev/null; then
        log_ok "前端服务 ✓ 运行正常"
    else
        log_warn "前端可能还在启动"
    fi

    # 显示容器状态
    echo ""
    log_do "容器状态："
    $COMPOSE_CMD ps
}

build_and_start

# ============================================
# 完成！显示访问信息
# ============================================

# 获取 IP
PUBLIC_IP=$(curl -sf --max-time 5 https://ipinfo.io/ip 2>/dev/null || \
            curl -sf --max-time 5 https://ifconfig.me 2>/dev/null || \
            curl -sf --max-time 5 https://api.ipify.org 2>/dev/null || \
            echo "")
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

F_PORT=$(grep -E "^FRONTEND_PORT=" "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2)
B_PORT=$(grep -E "^BACKEND_PORT=" "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2)
F_PORT=${F_PORT:-3999}
B_PORT=${B_PORT:-8899}

echo ""
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║            🎉  部署成功！系统已启动               ║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
if [ -n "$PUBLIC_IP" ]; then
echo -e "${GREEN}║${NC}  📊 ${BOLD}Dashboard 面板:${NC}                               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}http://${PUBLIC_IP}:${F_PORT}${NC}                          "
echo -e "${GREEN}║${NC}     http://${LOCAL_IP}:${F_PORT}  (内网)                     "
echo -e "${GREEN}║${NC}                                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  🔌 ${BOLD}API 健康检查:${NC}                                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}http://${PUBLIC_IP}:${B_PORT}/api/health${NC}                "
echo -e "${GREEN}║${NC}                                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  📡 ${BOLD}WebSocket:${NC}                                    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}ws://${PUBLIC_IP}:${B_PORT}/ws${NC}                          "
else
echo -e "${GREEN}║${NC}  📊 ${BOLD}Dashboard:${NC}  http://${LOCAL_IP}:${F_PORT}               "
echo -e "${GREEN}║${NC}  🔌 ${BOLD}API:${NC}        http://${LOCAL_IP}:${B_PORT}/api/health     "
echo -e "${GREEN}║${NC}  📡 ${BOLD}WebSocket:${NC}  ws://${LOCAL_IP}:${B_PORT}/ws               "
fi
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}常用命令:${NC}                                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  查看日志  ${CYAN}cd $INSTALL_DIR${NC}"
echo -e "${GREEN}║${NC}           ${CYAN}sudo docker logs -f polymarket-backend${NC}"
echo -e "${GREEN}║${NC}                                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  重启服务  ${CYAN}cd $INSTALL_DIR && $COMPOSE_CMD restart${NC}"
echo -e "${GREEN}║${NC}  停止服务  ${CYAN}cd $INSTALL_DIR && $COMPOSE_CMD down${NC}"
echo -e "${GREEN}║${NC}  编辑配置  ${CYAN}nano $INSTALL_DIR/.env${NC}"
echo -e "${GREEN}║${NC}                                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}更新部署（GitHub有新代码时）:${NC}                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}cd $INSTALL_DIR && git pull && $COMPOSE_CMD up -d --build${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║${NC}  ${YELLOW}⚠️  当前: DRY_RUN 模式（模拟，不真正下单）${NC}       ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${YELLOW}确认正常后: nano .env → DRY_RUN=false${NC}            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${YELLOW}然后: $COMPOSE_CMD restart${NC}                       ${GREEN}║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  安装目录: ${BOLD}$INSTALL_DIR${NC}"
echo ""