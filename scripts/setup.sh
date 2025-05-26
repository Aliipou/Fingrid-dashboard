#!/bin/bash
# Automated setup script for Fingrid Dashboard

set -e

echo "🔌 Setting up Fingrid Energy Dashboard..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.9+ is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_status "Python $python_version found"
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js 16+ is required but not installed"
        exit 1
    fi
    
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    print_status "Node.js v$node_version found"
    
    if command -v docker &> /dev/null; then
        print_status "Docker found (optional)"
    else
        print_warning "Docker not found (optional for containerized deployment)"
    fi
}

# Setup backend
setup_backend() {
    print_info "Setting up backend..."
    
    cd backend
    
    python3 -m venv venv
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    fi
    
    print_status "Backend dependencies installed"
    cd ..
}

# Setup frontend
setup_frontend() {
    print_info "Setting up frontend..."
    
    cd frontend
    npm install
    print_status "Frontend dependencies installed"
    cd ..
}

# Create environment files
create_env_files() {
    print_info "Creating environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_status "Environment file created"
        print_warning "Please edit .env with your actual API keys!"
    else
        print_info "Environment file already exists"
    fi
}

# Main setup function
main() {
    echo "🔌 Fingrid Energy Dashboard Setup"
    echo "=================================="
    echo ""
    
    check_prerequisites
    setup_backend
    setup_frontend
    create_env_files
    
    echo ""
    echo "🎉 Setup complete!"
    echo ""
    print_info "Next steps:"
    echo "1. Edit .env with your API keys from:"
    echo "   - Fingrid: https://data.fingrid.fi/"
    echo "   - Entso-E: https://transparency.entsoe.eu/"
    echo "2. Run: docker-compose up --build"
    echo "3. Open: http://localhost:3000"
    echo ""
    echo "Happy coding! 🚀"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi