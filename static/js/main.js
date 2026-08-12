document.addEventListener('DOMContentLoaded', function() {
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productData = {
                id: this.dataset.id || Date.now(),
                name: this.dataset.name,
                price: parseInt(this.dataset.price),
                size: this.dataset.size || 'M',
                image: this.dataset.image || ''
            };

            fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCartCount(data.cart_count);
                    showNotification('Товар добавлен в корзину');
                }
            });
        });
    });

    const removeButtons = document.querySelectorAll('.remove-item');
    removeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const itemId = parseInt(this.dataset.id);
            console.log('Removing item with ID:', itemId);

            fetch(`/api/cart/remove/${itemId}`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error removing item:', error);
            });
        });
    });

    const qtyInputs = document.querySelectorAll('.qty-input');
    qtyInputs.forEach(input => {
        input.addEventListener('change', function() {
            const itemId = parseInt(this.dataset.id);
            const quantity = parseInt(this.value);

            fetch('/api/cart/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: itemId, quantity: quantity })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        });
    });

    const decreaseButtons = document.querySelectorAll('.qty-btn.decrease');
    const increaseButtons = document.querySelectorAll('.qty-btn.increase');

    decreaseButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const input = document.querySelector(`.qty-input[data-id="${this.dataset.id}"]`);
            if (input && input.value > 1) {
                input.value = parseInt(input.value) - 1;
                input.dispatchEvent(new Event('change'));
            }
        });
    });

    increaseButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const input = document.querySelector(`.qty-input[data-id="${this.dataset.id}"]`);
            if (input) {
                input.value = parseInt(input.value) + 1;
                input.dispatchEvent(new Event('change'));
            }
        });
    });

    const checkoutBtn = document.getElementById('checkoutBtn');
    const checkoutModal = document.getElementById('checkoutModal');
    const closeModal = document.querySelector('.close-modal');
    const successModal = document.getElementById('successModal');

    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function() {
            if (checkoutModal) {
                checkoutModal.classList.add('active');
            }
        });
    }

    if (closeModal) {
        closeModal.addEventListener('click', function() {
            checkoutModal.classList.remove('active');
        });
    }



    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    let lastScroll = 0;
    const header = document.querySelector('.main-header');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            header.style.background = 'rgba(10, 10, 10, 0.98)';
        } else {
            header.style.background = 'rgba(10, 10, 10, 0.95)';
        }

        lastScroll = currentScroll;
    });

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.product-card, .collection-card, .preorder-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease';
        observer.observe(el);
    });
});

function updateCartCount(count) {
    const cartCount = document.getElementById('cartCount');
    if (cartCount) {
        cartCount.textContent = count;
        if (count > 0) {
            cartCount.style.display = 'flex';
            // Анимация при изменении
            cartCount.style.transform = 'scale(1.3)';
            setTimeout(() => {
                cartCount.style.transform = 'scale(1)';
            }, 200);
        } else {
            cartCount.style.display = 'none';
        }
    }
}

function getCartCount() {
    return fetch('/api/cart/count')
        .then(response => response.json())
        .then(data => data.count)
        .catch(() => 0);
}

document.addEventListener('DOMContentLoaded', function() {
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productData = {
                id: this.dataset.id || Date.now(),
                name: this.dataset.name,
                price: parseInt(this.dataset.price),
                size: this.dataset.size || 'M',
                image: this.dataset.image || ''
            };

            fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCartCount(data.cart_count);
                    showNotification('Товар добавлен в корзину');
                }
            });
        });
    });

    let lastScroll = 0;
    const header = document.querySelector('.main-header');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            header.style.background = 'rgba(10, 10, 10, 0.98)';
        } else {
            header.style.background = 'rgba(10, 10, 10, 0.95)';
        }

        lastScroll = currentScroll;
    });

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: var(--white);
        color: var(--black);
        padding: 20px 30px;
        z-index: 3000;
        animation: slideIn 0.3s ease;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    #cartCount {
        transition: transform 0.2s ease;
    }
`;
document.head.appendChild(style);

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: var(--white);
        color: var(--black);
        padding: 20px 30px;
        z-index: 3000;
        animation: slideIn 0.3s ease;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', function() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');

                // Для секций с текстом
                if (entry.target.classList.contains('about-content')) {
                    entry.target.classList.add('visible');
                }
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll(
        '.animate-on-scroll, .animate-fade-up, .animate-fade-left, .animate-fade-right, .animate-zoom-in, .animate-scale-up'
    );

    animatedElements.forEach(el => {
        observer.observe(el);
    });

    const sections = document.querySelectorAll('section');
    sections.forEach(section => {
        observer.observe(section);
    });

    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach((card, index) => {
        card.classList.add('animate-on-scroll', `delay-${(index % 5) + 1}`);
        observer.observe(card);
    });

    const collectionCards = document.querySelectorAll('.collection-card');
    collectionCards.forEach((card, index) => {
        card.classList.add('animate-on-scroll', `delay-${(index % 5) + 1}`);
        observer.observe(card);
    });

    const galleryItems = document.querySelectorAll('.gallery-item');
    galleryItems.forEach((item, index) => {
        item.classList.add('animate-on-scroll', `delay-${(index % 5) + 1}`);
        observer.observe(item);
    });

    const socialCards = document.querySelectorAll('.social-card');
    socialCards.forEach((card, index) => {
        card.classList.add('animate-on-scroll', `delay-${(index % 5) + 1}`);
        observer.observe(card);
    });

    const sectionTitles = document.querySelectorAll('.section-title');
    sectionTitles.forEach(title => {
        title.classList.add('animate-on-scroll');
        observer.observe(title);
    });

    const aboutContent = document.querySelector('.about-content');
    if (aboutContent) {
        observer.observe(aboutContent);
    }

    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);
});

document.body.style.opacity = '0';
document.body.style.transition = 'opacity 0.5s ease';

function createThreadConnections() {
    const threadContainer = document.getElementById('threadConnections');
    if (!threadContainer) return;

    const collectionPins = document.querySelectorAll('.collection-pin');
    if (collectionPins.length < 2) return;

    threadContainer.innerHTML = '';

    const boardRect = threadContainer.parentElement.getBoundingClientRect();

    for (let i = 0; i < collectionPins.length - 1; i++) {
        const currentPin = collectionPins[i];
        const nextPin = collectionPins[i + 1];

        const currentRect = currentPin.getBoundingClientRect();
        const nextRect = nextPin.getBoundingClientRect();

        const currentCenterY = currentRect.top + currentRect.height / 2;
        const nextCenterY = nextRect.top + nextRect.height / 2;

        if (Math.abs(currentCenterY - nextCenterY) > 150) {
            continue;
        }

        const currentCenterX = currentRect.left + currentRect.width / 2;
        const nextCenterX = nextRect.left + nextRect.width / 2;

        const startX = currentCenterX - boardRect.left;
        const startY = currentCenterY - boardRect.top;
        const endX = nextCenterX - boardRect.left;
        const endY = nextCenterY - boardRect.top;

        const length = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));

        const angle = Math.atan2(endY - startY, endX - startX) * 180 / Math.PI;

        const thread = document.createElement('div');
        thread.className = 'thread-line';
        thread.style.width = length + 'px';
        thread.style.left = startX + 'px';
        thread.style.top = startY + 'px';
        thread.style.transform = `rotate(${angle}deg)`;

        const leftPin = document.createElement('div');
        leftPin.className = 'thread-pin left';

        const rightPin = document.createElement('div');
        rightPin.className = 'thread-pin right';

        thread.appendChild(leftPin);
        thread.appendChild(rightPin);

        threadContainer.appendChild(thread);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(createThreadConnections, 800);
    window.addEventListener('resize', createThreadConnections);
});