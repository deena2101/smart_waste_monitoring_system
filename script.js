// script.js - Smart Waste Monitoring Interactivity

document.addEventListener('DOMContentLoaded', () => {
    // Animate progress bars on load
    const progressBars = document.querySelectorAll('.progress-bar .progress');
    progressBars.forEach(bar => {
        // Store original width
        const originalWidth = bar.style.width;
        // Set to 0 temporarily for animation
        bar.style.width = '0%';
        // Add a small delay for visual effect
        setTimeout(() => {
            bar.style.width = originalWidth;
        }, 300);
    });

    // Sidebar Navigation Active states
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const link = item.querySelector('a');
            if (link && link.getAttribute('href') === '#') {
                e.preventDefault();
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');
            }
        });
    });

    // Filter Tabs
    const tabs = document.querySelectorAll('.filter-tabs .tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const filterType = tab.textContent.trim().toLowerCase();
            const binCards = document.querySelectorAll('.bin-card');
            
            binCards.forEach(card => {
                const statusBadge = card.querySelector('.status-badge');
                let shouldShow = false;
                
                if (filterType === 'all') {
                    shouldShow = true;
                } else if (filterType === 'critical') {
                    shouldShow = statusBadge && statusBadge.classList.contains('full');
                } else if (filterType === 'claimed') {
                    shouldShow = statusBadge && statusBadge.classList.contains('claimed');
                }
                
                if (shouldShow) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });

    // Search functionality
    const searchInput = document.getElementById('bin-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const binCards = document.querySelectorAll('.bin-card');
            
            // If searching, reset the tab filters visually to "All" (makes logic simpler)
            if (searchTerm.length > 0) {
                const tabs = document.querySelectorAll('.filter-tabs .tab');
                if(tabs.length > 0) {
                    tabs.forEach(t => t.classList.remove('active'));
                    tabs[0].classList.add('active'); // 'All'
                }
            }

            binCards.forEach(card => {
                const binNameObj = card.querySelector('h3');
                const binName = binNameObj ? binNameObj.textContent.toLowerCase() : '';
                
                const statusObj = card.querySelector('.status-badge');
                const statusBadge = statusObj ? statusObj.textContent.toLowerCase() : '';

                if (binName.includes(searchTerm) || statusBadge.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Toggle Notifications
    const notificationBtn = document.getElementById('notification-btn');
    const notificationDropdown = document.getElementById('notifications-dropdown');

    if (notificationBtn && notificationDropdown) {
        notificationBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationDropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!notificationBtn.contains(e.target) && !notificationDropdown.contains(e.target)) {
                notificationDropdown.classList.remove('show');
            }
        });
    }

    // Disable non-full bins visually
    const binCards = document.querySelectorAll('.bin-card');
    binCards.forEach(card => {
        const statusBadge = card.querySelector('.status-badge');
        const claimBtn = card.querySelector('.btn-outline');
        if (statusBadge && claimBtn) {
            const status = statusBadge.textContent.trim().toLowerCase();
            if (status !== 'full' && status !== 'critical' && status !== 'claimed') {
                claimBtn.style.opacity = '0.7';
                claimBtn.title = 'Bin must be on alert to claim';
            }
        }
    });

});

/**
 * Handle worker claiming a bin
 * @param {HTMLButtonElement} btn 
 */
function claimBin(btn) {
    if (btn.classList.contains('disabled') || btn.disabled) return;
    
    // Find the relevant card
    const card = btn.closest('.bin-card');
    const statusBadge = card.querySelector('.status-badge');
    
    // Disallow claiming if not full or critical
    if (statusBadge) {
        const text = statusBadge.textContent.trim().toLowerCase();
        if (text !== 'full' && text !== 'critical') {
            alert('You can only claim bins that are critically full (on alert).');
            return;
        }
    }

    // Update button text and state
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    // Simulate API call to claim the bin
    setTimeout(() => {
        // Change button to claimed state
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Claimed';
        btn.classList.add('disabled');

        // Update status badge
        statusBadge.textContent = 'Claimed';
        statusBadge.className = 'status-badge claimed';

        // Add subtle animation to the card to indicate success
        card.style.transform = 'scale(0.98)';
        setTimeout(() => {
            card.style.transform = '';
            // Show a simple success notification
            simulateNewNotification(card.querySelector('h3').textContent);
        }, 150);

    }, 800);
}

/**
 * Simulate a new notification entry
 */
function simulateNewNotification(binType) {
    const list = document.querySelector('.history-list');
    const date = new Date();
    const timeString = 'Just now';

    // Get class modifier based on bin type
    const typeLower = binType.toLowerCase();
    let iconClass = 'fa-trash-can text-unclassified';
    let bgClass = 'bg-unclassified-light';

    if (typeLower.includes('plastic')) { iconClass = 'fa-bottle-water text-plastic'; bgClass = 'bg-plastic-light'; }
    if (typeLower.includes('organic')) { iconClass = 'fa-apple-whole text-organic'; bgClass = 'bg-organic-light'; }
    if (typeLower.includes('paper')) { iconClass = 'fa-newspaper text-paper'; bgClass = 'bg-paper-light'; }

    const newDoc = document.createElement('li');
    newDoc.style.opacity = '0';
    newDoc.style.transform = 'translateY(-10px)';
    newDoc.style.transition = 'all 0.4s ease';

    newDoc.innerHTML = `
        <div class="history-icon ${bgClass}">
            <i class="fa-solid ${iconClass}"></i>
        </div>
        <div class="history-details">
            <p class="title">${binType} bin claimed</p>
            <p class="time">${timeString}</p>
        </div>
        <span class="points">+5 pts</span>
    `;

    list.prepend(newDoc);

    // Animate in
    setTimeout(() => {
        newDoc.style.opacity = '1';
        newDoc.style.transform = 'translateY(0)';
    }, 50);

    // Remove last item to keep list small
    if (list.children.length > 4) {
        list.lastElementChild.remove();
    }

    // Update score if it exists on the page
    const scoreNum = document.querySelector('.score .number');
    if (scoreNum) {
        let currentScore = parseInt(scoreNum.textContent.replace(',', ''));
        scoreNum.textContent = (currentScore + 5).toLocaleString();
    }
}

/**
 * Handle worker updating collection
 * @param {HTMLButtonElement} btn 
 */
function updateCollection(btn) {
    if (btn.disabled) return;

    const card = btn.closest('.bin-card');
    const binName = card.querySelector('h3').textContent;
    const claimBtn = card.querySelector('.btn-outline');

    // Only allow update if claimed
    if (!claimBtn.classList.contains('disabled')) {
        alert("You must claim this bin first before updating the collection!");
        return;
    }

    // Process collection
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    setTimeout(() => {
        // Reset Bin UI completely

        // 1. Reset Progress bar
        const progressBar = card.querySelector('.progress');
        progressBar.style.width = '0%';
        const percentageText = card.querySelector('.percentage');
        percentageText.textContent = '0%';

        // 2. Reset Status Badge
        const statusBadge = card.querySelector('.status-badge');
        statusBadge.textContent = 'Empty';
        statusBadge.className = 'status-badge empty';

        // 3. Reset Buttons
        claimBtn.innerHTML = '<i class="fa-solid fa-hand-holding-hand"></i> Claim Bin';
        claimBtn.classList.remove('disabled');
        claimBtn.disabled = false;
        claimBtn.style.opacity = '0.7';

        btn.innerHTML = originalText;
        btn.disabled = false;

        // 4. Success Animation
        card.style.transform = 'scale(0.98)';
        setTimeout(() => {
            card.style.transform = '';
            simulateCollectionNotification(binName);
        }, 150);

    }, 1000);
}

/**
 * Simulate a collection notification entry
 */
function simulateCollectionNotification(binType) {
    const list = document.querySelector('.history-list');
    if (!list) return; // if not on dashboard page

    const timeString = 'Just now';

    // Get class modifier based on bin type
    const typeLower = binType.toLowerCase();
    let iconClass = 'fa-trash-can text-unclassified';
    let bgClass = 'bg-unclassified-light';

    if (typeLower.includes('plastic')) { iconClass = 'fa-bottle-water text-plastic'; bgClass = 'bg-plastic-light'; }
    if (typeLower.includes('organic')) { iconClass = 'fa-apple-whole text-organic'; bgClass = 'bg-organic-light'; }
    if (typeLower.includes('paper')) { iconClass = 'fa-newspaper text-paper'; bgClass = 'bg-paper-light'; }

    const newDoc = document.createElement('li');
    newDoc.style.opacity = '0';
    newDoc.style.transform = 'translateY(-10px)';
    newDoc.style.transition = 'all 0.4s ease';

    newDoc.innerHTML = `
        <div class="history-icon ${bgClass}">
            <i class="fa-solid ${iconClass}"></i>
        </div>
        <div class="history-details">
            <p class="title">${binType} collection updated</p>
            <p class="time">${timeString}</p>
        </div>
        <span class="points">+25 pts</span>
    `;

    list.prepend(newDoc);

    // Animate in
    setTimeout(() => {
        newDoc.style.opacity = '1';
        newDoc.style.transform = 'translateY(0)';
    }, 50);

    if (list.children.length > 4) {
        list.lastElementChild.remove();
    }

    // Update score by a larger amount for collection
    const scoreNum = document.querySelector('.score .number');
    if (scoreNum) {
        let currentScore = parseInt(scoreNum.textContent.replace(',', ''));
        scoreNum.textContent = (currentScore + 25).toLocaleString();
    }
}

/**
 * Handle Trip Saver Modal
 */
function showTripModal() {
    const modal = document.getElementById('route-modal'); // Reusing the same ID for simplicity
    if (modal) {
        modal.classList.add('show');
        const dropdown = document.getElementById('notifications-dropdown');
        if (dropdown) dropdown.classList.remove('show');
    }
}

function closeTripModal() {
    const modal = document.getElementById('route-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function acceptTrip(btn) {
    if (!btn) {
        // Fallback if not passed explicitly, though we'll update the HTML to pass `this`
        btn = document.querySelector('.modal-footer .btn-primary');
    }
    
    if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
        btn.disabled = true;
        
        setTimeout(() => {
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Strategy Assigned';
            setTimeout(() => {
                closeTripModal();
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 800);
        }, 1000);
    }
}
