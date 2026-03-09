#!/bin/bash
# deploy.sh - 一键部署脚本

set -e

echo "╔══════════════════════════════════════════╗"
echo "║  🤖 Polymarket 套利系统 - 一键部署       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装${NC}"
        echo "请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker 已安装${NC}"
}

# 创建目录结构
setup_dirs() {
    echo -e "${BLUE}📁 创建目录结构...${NC}"
    mkdir -p data logs backend/agents backend/services backend/utils frontend/src/components frontend/src/hooks frontend/public
    echo -e "${GREEN}✅ 目录创建完成${NC}"
}

# 配置环境变量
setup_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}📝 创建 .env 配置文件...${NC}"
        cp .env.example .env
        echo ""
        echo -e "${YELLOW}⚠️  请编辑 .env 文件配置你的 API Keys:${NC}"
        echo "   nano .env"
        echo ""
        echo "   必须配置:"
        echo "   - POLYMARKET_API_KEY"
        echo "   - POLYMARKET_API_SECRET"
        echo ""
        echo "   推荐配置:"
        echo "   - NOAA_API_TOKEN (天气Agent)"
        echo "   - BINANCE_API_KEY (加密货币Agent)"
        echo "   - NEWSAPI_KEY (新闻Agent)"
        echo ""
        echo -e "${YELLOW}   首次使用建议保持 DRY_RUN=true${NC}"
        echo ""
        read -p "配置完成后按 Enter 继续..."
    else
        echo -e "${GREEN}✅ .env 文件已存在${NC}"
    fi
}

# 构建并启动
build_and_start() {
    echo -e "${BLUE}🔨 构建 Docker 镜像...${NC}"

    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    $COMPOSE_CMD build --no-cache
    echo -e "${GREEN}✅ 构建完成${NC}"

    echo -e "${BLUE}🚀 启动服务...${NC}"
    $COMPOSE_CMD up -d

    echo ""
    echo -e "${GREEN}✅ 部署完成！${NC}"
    echo ""
}

# 显示访问信息
show_info() {
    # 获取服务器IP
    SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

    echo "╔══════════════════════════════════════════╗"
    echo "║           🎉 部署成功！                   ║"
    echo "╠══════════════════════════════════════════╣"
    echo "║                                          ║"
    echo "║  📊 Dashboard:                           ║"
    echo "║     http://${SERVER_IP}:3999              "
    echo "║                                          ║"
    echo "║  🔌 API:                                 ║"
    echo "║     http://${SERVER_IP}:8899/api/health   "
    echo "║                                          ║"
    echo "║  🔌 WebSocket:                           ║"
    echo "║     ws://${SERVER_IP}:8899/ws             "
    echo "║                                          ║"
    echo "╠══════════════════════════════════════════╣"
    echo "║  常用命令:                                ║"
    echo "║  查看日志: docker logs -f polymarket-backend"
    echo "║  停止服务: docker compose down            ║"
    echo "║  重启服务: docker compose restart          ║"
    echo "╚══════════════════════════════════════════╝"
}

# 主流程
main() {
    check_docker
    setup_dirs
    setup_env
    build_and_start
    show_info
}

main "$@"