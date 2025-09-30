echo "🏦 Bank AI Data Analyst ishga tushirilmoqda..."
echo "=============================================="

RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port > /dev/null 2>&1; then
            print_status "$service ishlaydi (port $port)"
            return 0
        fi
        
        print_info "$service kutilmoqda... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    print_error "$service ishlamadi (port $port)"
    return 1
}

print_info "Ollama service ishga tushirilmoqda..."
ollama serve &
OLLAMA_PID=$!

if check_service "Ollama" 11434; then
    print_info "Llama3.2 model yuklab olinmoqda..."
    if ollama pull llama3.2; then
        print_status "Model muvaffaqiyatli yuklandi"
    else
        print_error "Model yuklanmadi, lekin davom etamiz"
    fi
else
    print_error "Ollama service ishlamadi!"
fi

if [ -d "venv" ]; then
    print_info "Virtual environment faollashtirilmoqda..."
    source venv/bin/activate
    print_status "Virtual environment faol"
else
    print_info "Virtual environment topilmadi, global Python ishlatilmoqda"
fi

if [ ! -f "bank_data.db" ]; then
    print_info "Database yaratilmoqda (1M+ yozuv)..."
    if timeout 300 python bank_analyst.py --setup; then
        print_status "Database muvaffaqiyatli yaratildi"
    else
        print_error "Database yaratishda muammo"
    fi
else
    print_status "Database mavjud"
fi

mkdir -p reports logs templates
print_status "Papkalar yaratildi"

print_info "Web application ishga tushirilmoqda..."
print_info "URL: http://localhost:5000"
print_info "Ollama API: http://localhost:11434"

cleanup() {
    print_info "Cleanup..."
    kill $OLLAMA_PID 2>/dev/null || true
    exit
}
trap cleanup EXIT INT TERM

if python web_app.py; then
    print_status "Web application ishga tushdi"
else
    print_error "Web application xatosi"
    
    print_info "Fallback: simple HTTP server..."
    python -m http.server 5000
fi