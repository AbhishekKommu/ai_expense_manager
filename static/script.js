// ============ PARTICLES ANIMATION ============
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (Math.random() * 10 + 8) + 's';
        particle.style.animationDelay = Math.random() * 5 + 's';
        particle.style.width = particle.style.height = (Math.random() * 4 + 2) + 'px';
        particle.style.opacity = Math.random() * 0.5 + 0.3;
        particlesContainer.appendChild(particle);
    }
}

// ============ CATEGORY ICONS ============
const categoryIcons = {
    'Food': '🍔',
    'Transport': '🚗',
    'Shopping': '🛍️',
    'Bills': '📄',
    'Entertainment': '🎬',
    'Health': '💊',
    'Other': '📦'
};

// ============ FORMAT CURRENCY ============
function formatCurrency(amount) {
    return '$' + parseFloat(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ============ FORMAT DATE ============
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// ============ TOAST NOTIFICATION ============
function showToast(message, isError = false) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) existingToast.remove();
    
    const toast = document.createElement('div');
    toast.className = 'toast' + (isError ? ' error' : '');
    toast.innerHTML = `<i class="fas ${isError ? 'fa-exclamation-circle' : 'fa-check-circle'}"></i> ${message}`;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// ============ LOAD EXPENSES ============
async function loadExpenses() {
    try {
        const response = await fetch('/api/expenses');
        const data = await response.json();
        
        // Update total
        document.getElementById('totalAmount').textContent = formatCurrency(data.total);
        
        // Render list
        const listContainer = document.getElementById('expensesList');
        
        if (data.expenses.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No expenses yet. Add your first expense!</p>
                </div>
            `;
            return;
        }
        
        listContainer.innerHTML = data.expenses.map(exp => `
            <div class="expense-item">
                <div class="expense-info">
                    <div class="expense-category">
                        ${categoryIcons[exp.category] || '📦'}
                    </div>
                    <div class="expense-details">
                        <h4>${exp.description}</h4>
                        <p>${exp.category} • ${formatDate(exp.date)}</p>
                    </div>
                </div>
                <div style="display: flex; align-items: center;">
                    <div class="expense-amount">${formatCurrency(exp.amount)}</div>
                    <button class="btn-delete" onclick="deleteExpense(${exp.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading expenses:', error);
        showToast('Failed to load expenses', true);
    }
}

// ============ ADD EXPENSE ============
async function addExpense(e) {
    e.preventDefault();
    
    const description = document.getElementById('description').value;
    const amount = document.getElementById('amount').value;
    const category = document.getElementById('category').value;
    const date = document.getElementById('date').value || new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch('/api/expenses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description, amount, category, date })
        });
        
        if (response.ok) {
            showToast('Expense added successfully!');
            document.getElementById('expenseForm').reset();
            loadExpenses();
        } else {
            showToast('Failed to add expense', true);
        }
    } catch (error) {
        console.error('Error adding expense:', error);
        showToast('Failed to add expense', true);
    }
}

// ============ DELETE EXPENSE ============
async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) return;
    
    try {
        const response = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('Expense deleted!');
            loadExpenses();
        }
    } catch (error) {
        console.error('Error deleting expense:', error);
        showToast('Failed to delete expense', true);
    }
}

// ============ INITIALIZE ============
document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    loadExpenses();
    
    // Set today's date as default
    document.getElementById('date').value = new Date().toISOString().split('T')[0];
    
    // Form submit
    document.getElementById('expenseForm').addEventListener('submit', addExpense);
});