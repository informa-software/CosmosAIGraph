// Contract Workbench JavaScript
// Implements functionality equivalent to the React mock UI

// Mock Data (to be replaced with API calls)
const MOCK_CONTRACTS = [
    {
        id: "C-001",
        title: "Master Services Agreement – Asterix Health",
        counterparty: "Asterix Health, Inc.",
        effective: "2024-11-02",
        law: "New York",
        type: "MSA",
        risk: "Med",
        clauses: {
            Indemnity: "Each party shall indemnify, defend, and hold harmless the other from third-party claims arising out of gross negligence or willful misconduct.",
            "Limitation of Liability": "Neither party shall be liable for indirect or consequential damages; aggregate liability shall not exceed 12 months of fees.",
            "Payment Terms": "Net 45 days from invoice date; 1% monthly late fee.",
            Insurance: "Commercial general liability $2M, cyber liability $3M, workers' compensation statutory.",
            "Governing Law": "This Agreement is governed by the laws of the State of New York, without regard to conflicts principles.",
        },
    },
    {
        id: "C-002",
        title: "Subscription Agreement – Novalink",
        counterparty: "Novalink LLC",
        effective: "2025-03-18",
        law: "Delaware",
        type: "Subscription",
        risk: "Low",
        clauses: {
            Indemnity: "Vendor will indemnify Customer against third-party IP infringement claims subject to prompt notice and sole control of the defense.",
            "Limitation of Liability": "EXCEPT FOR FRAUD OR INTENTIONAL MISCONDUCT, LIABILITY IS CAPPED AT FEES PAID IN THE SIX (6) MONTHS PRECEDING THE CLAIM.",
            "Payment Terms": "Net 30; 0.5% monthly late fee.",
            Insurance: "CGL $1M, cyber $1M.",
            "Governing Law": "This Agreement and any dispute shall be governed by the laws of the State of Delaware.",
        },
    },
    {
        id: "C-003",
        title: "Professional Services SOW – BlueFerry",
        counterparty: "BlueFerry Corp",
        effective: "2023-09-01",
        law: "California",
        type: "SOW",
        risk: "High",
        clauses: {
            Indemnity: "Vendor shall indemnify Customer for claims alleging bodily injury, death, or damage to tangible property caused by Vendor's performance.",
            "Limitation of Liability": "Total cumulative liability shall not exceed the greater of $500,000 or amounts paid in the 3 months preceding the event.",
            "Payment Terms": "Milestone-based; 40/40/20 with 10-day review windows.",
            Insurance: "CGL $2M, professional liability $1M.",
            "Governing Law": "This Statement of Work is governed by the laws of the State of California.",
        },
    },
];

const CLAUSE_KEYS = ["Indemnity", "Limitation of Liability", "Payment Terms", "Insurance", "Governing Law"];
const PROVISION_KEYS = [
    "Payment Terms",
    "Insurance", 
    "Limitation of Liability",
    "Termination",
    "Service Levels",
    "Confidentiality",
];

// Gold standard baseline (from C-002)
const GOLD_STANDARD = {
    "Payment Terms": "Net 30; 0.5% monthly late fee.",
    "Insurance": "CGL $1M, cyber $1M.",
    "Limitation of Liability": "EXCEPT FOR FRAUD OR INTENTIONAL MISCONDUCT, LIABILITY IS CAPPED AT FEES PAID IN THE SIX (6) MONTHS PRECEDING THE CLAIM.",
};

// State Management
let state = {
    filters: {
        mode: "batch",
        type: "Any",
        dateFrom: "",
        dateTo: "",
        clauses: [],
        provisions: [],
        risk: 50,
    },
    searchText: "",
    question: "Which contracts are governed by states other than Delaware?",
    picked: [],
    contracts: [], // Will be populated from API
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initializeUI();
    loadContracts();
    setupEventListeners();
});

function initializeUI() {
    // Initialize clause options
    const clauseOptions = document.getElementById("clauseOptions");
    CLAUSE_KEYS.forEach(clause => {
        const div = document.createElement("div");
        div.className = "form-check";
        div.innerHTML = `
            <input class="form-check-input clause-checkbox" type="checkbox" value="${clause}" id="clause_${clause.replace(/\s/g, '_')}">
            <label class="form-check-label" for="clause_${clause.replace(/\s/g, '_')}">${clause}</label>
        `;
        clauseOptions.appendChild(div);
    });

    // Initialize provision options
    const provisionOptions = document.getElementById("provisionOptions");
    PROVISION_KEYS.forEach(provision => {
        const div = document.createElement("div");
        div.className = "form-check";
        div.innerHTML = `
            <input class="form-check-input provision-checkbox" type="checkbox" value="${provision}" id="provision_${provision.replace(/\s/g, '_')}">
            <label class="form-check-label" for="provision_${provision.replace(/\s/g, '_')}">${provision}</label>
        `;
        provisionOptions.appendChild(div);
    });

    // Set initial question
    document.getElementById("questionText").value = state.question;
}

async function loadContracts() {
    // In production, this would be an API call
    // For now, use mock data
    state.contracts = MOCK_CONTRACTS;
    
    // Try to fetch real contracts from API
    try {
        const response = await fetch('/api/contracts');
        if (response.ok) {
            const data = await response.json();
            if (data.contracts && data.contracts.length > 0) {
                state.contracts = data.contracts;
            }
        }
    } catch (error) {
        console.log('Using mock contracts data:', error);
    }
    
    updateContractsList();
    updateContractsTable();
    updateJurisdictionInsights();
}

function setupEventListeners() {
    // Mode selection
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            state.filters.mode = e.target.value;
            updateModeLimits();
        });
    });

    // Contract type selection
    document.getElementById("contractType").addEventListener("change", (e) => {
        state.filters.type = e.target.value;
        const dateSection = document.getElementById("dateRangeSection");
        if (e.target.value !== "Any") {
            dateSection.classList.remove("d-none");
        } else {
            dateSection.classList.add("d-none");
        }
        updateAvailableContracts();
    });

    // Date range
    document.getElementById("dateFrom").addEventListener("change", (e) => {
        state.filters.dateFrom = e.target.value;
        updateAvailableContracts();
    });

    document.getElementById("dateTo").addEventListener("change", (e) => {
        state.filters.dateTo = e.target.value;
        updateAvailableContracts();
    });

    // Risk threshold
    document.getElementById("riskThreshold").addEventListener("input", (e) => {
        state.filters.risk = parseInt(e.target.value);
        document.getElementById("riskValue").textContent = e.target.value;
    });

    // Clause selection
    document.querySelectorAll(".clause-checkbox").forEach(checkbox => {
        checkbox.addEventListener("change", (e) => {
            if (e.target.checked) {
                const maxClauses = state.filters.mode === "realtime" ? 3 : CLAUSE_KEYS.length;
                if (state.filters.clauses.length < maxClauses) {
                    state.filters.clauses.push(e.target.value);
                    // Clear provisions if clauses selected
                    state.filters.provisions = [];
                    updateProvisionCheckboxes();
                } else {
                    e.target.checked = false;
                }
            } else {
                state.filters.clauses = state.filters.clauses.filter(c => c !== e.target.value);
            }
            updateClauseBadges();
            updateClauseProvisionButtons();
        });
    });

    // Provision selection
    document.querySelectorAll(".provision-checkbox").forEach(checkbox => {
        checkbox.addEventListener("change", (e) => {
            if (e.target.checked) {
                const maxProvisions = state.filters.mode === "realtime" ? 3 : PROVISION_KEYS.length;
                if (state.filters.provisions.length < maxProvisions) {
                    state.filters.provisions.push(e.target.value);
                    // Clear clauses if provisions selected
                    state.filters.clauses = [];
                    updateClauseCheckboxes();
                } else {
                    e.target.checked = false;
                }
            } else {
                state.filters.provisions = state.filters.provisions.filter(p => p !== e.target.value);
            }
            updateProvisionBadges();
            updateClauseProvisionButtons();
        });
    });

    // Search text
    document.getElementById("searchText").addEventListener("input", (e) => {
        state.searchText = e.target.value;
        updateContractsTable();
    });

    // Question text
    document.getElementById("questionText").addEventListener("input", (e) => {
        state.question = e.target.value;
    });

    // Apply filters
    document.getElementById("applyFilters").addEventListener("click", applyFilters);

    // Get answer
    document.getElementById("getAnswer").addEventListener("click", getAnswer);

    // Compare selected
    document.getElementById("compareSelected").addEventListener("click", compareSelected);

    // Copy results
    document.getElementById("copyResults").addEventListener("click", copyResults);

    // Contract selection modal buttons
    document.getElementById("selectAll").addEventListener("click", selectAllContracts);
    document.getElementById("deselectAll").addEventListener("click", deselectAllContracts);
}

function updateModeLimits() {
    const realtimeLimits = document.getElementById("realtimeLimits");
    const clauseCap = document.getElementById("clauseCap");
    
    if (state.filters.mode === "realtime") {
        realtimeLimits.classList.remove("d-none");
        clauseCap.textContent = "3";
        
        // Enforce limits
        if (state.picked.length > 3) {
            state.picked = state.picked.slice(0, 3);
        }
        if (state.filters.clauses.length > 3) {
            state.filters.clauses = state.filters.clauses.slice(0, 3);
        }
        if (state.filters.provisions.length > 3) {
            state.filters.provisions = state.filters.provisions.slice(0, 3);
        }
    } else {
        realtimeLimits.classList.add("d-none");
        clauseCap.textContent = CLAUSE_KEYS.length;
    }
    
    updateSelectedCount();
    updateClauseCheckboxes();
    updateProvisionCheckboxes();
}

function updateAvailableContracts() {
    const filtered = getFilteredContracts();
    updateContractsList();
    updateContractsTable();
}

function getFilteredContracts() {
    return state.contracts.filter(contract => {
        // Type filter
        if (state.filters.type !== "Any" && contract.type !== state.filters.type) {
            return false;
        }
        
        // Date filter
        if (state.filters.type !== "Any") {
            const effectiveDate = new Date(contract.effective);
            if (state.filters.dateFrom && effectiveDate < new Date(state.filters.dateFrom)) {
                return false;
            }
            if (state.filters.dateTo && effectiveDate > new Date(state.filters.dateTo)) {
                return false;
            }
        }
        
        // Search text filter
        if (state.searchText) {
            const searchLower = state.searchText.toLowerCase();
            const clauseMatch = CLAUSE_KEYS.some(key => 
                contract.clauses[key] && 
                contract.clauses[key].toLowerCase().includes(searchLower)
            );
            if (!clauseMatch) {
                return false;
            }
        }
        
        return true;
    });
}

function updateContractsList() {
    const list = document.getElementById("contractSelectionList");
    const filtered = getFilteredContracts();
    
    list.innerHTML = "";
    filtered.forEach(contract => {
        const isSelected = state.picked.includes(contract.id);
        const div = document.createElement("div");
        div.className = "list-group-item bg-dark text-light";
        div.innerHTML = `
            <div class="form-check">
                <input class="form-check-input contract-checkbox" type="checkbox" 
                       value="${contract.id}" id="contract_${contract.id}"
                       ${isSelected ? 'checked' : ''}>
                <label class="form-check-label w-100" for="contract_${contract.id}">
                    <div class="d-flex justify-content-between">
                        <span><strong>${contract.id}</strong> - ${contract.title}</span>
                        <div>
                            <span class="badge bg-secondary">${contract.type}</span>
                            <span class="badge bg-info">${contract.effective}</span>
                        </div>
                    </div>
                </label>
            </div>
        `;
        list.appendChild(div);
        
        // Add event listener
        div.querySelector(".contract-checkbox").addEventListener("change", (e) => {
            toggleContractSelection(contract.id);
        });
    });
}

function toggleContractSelection(contractId) {
    const maxContracts = state.filters.mode === "realtime" ? 3 : 999;
    const index = state.picked.indexOf(contractId);
    
    if (index === -1) {
        if (state.picked.length < maxContracts) {
            state.picked.push(contractId);
        }
    } else {
        state.picked.splice(index, 1);
    }
    
    updateSelectedCount();
    updateContractsTable();
    updateClauseCompare();
}

function selectAllContracts() {
    const filtered = getFilteredContracts();
    const maxContracts = state.filters.mode === "realtime" ? 3 : 999;
    
    filtered.forEach(contract => {
        if (!state.picked.includes(contract.id) && state.picked.length < maxContracts) {
            state.picked.push(contract.id);
        }
    });
    
    updateContractsList();
    updateSelectedCount();
}

function deselectAllContracts() {
    const filtered = getFilteredContracts();
    const filteredIds = filtered.map(c => c.id);
    state.picked = state.picked.filter(id => !filteredIds.includes(id));
    
    updateContractsList();
    updateSelectedCount();
}

function updateSelectedCount() {
    document.getElementById("selectedCount").textContent = state.picked.length;
    document.getElementById("modalSelectedCount").textContent = `${state.picked.length} selected`;
    document.getElementById("compareCount").textContent = state.picked.length;
}

function updateClauseCheckboxes() {
    document.querySelectorAll(".clause-checkbox").forEach(checkbox => {
        checkbox.checked = state.filters.clauses.includes(checkbox.value);
        checkbox.disabled = state.filters.provisions.length > 0;
    });
}

function updateProvisionCheckboxes() {
    document.querySelectorAll(".provision-checkbox").forEach(checkbox => {
        checkbox.checked = state.filters.provisions.includes(checkbox.value);
        checkbox.disabled = state.filters.clauses.length > 0;
    });
}

function updateClauseBadges() {
    const container = document.getElementById("selectedClauses");
    container.innerHTML = "";
    state.filters.clauses.forEach(clause => {
        const badge = document.createElement("span");
        badge.className = "badge bg-secondary me-1";
        badge.textContent = clause;
        container.appendChild(badge);
    });
}

function updateProvisionBadges() {
    const container = document.getElementById("selectedProvisions");
    container.innerHTML = "";
    state.filters.provisions.forEach(provision => {
        const badge = document.createElement("span");
        badge.className = "badge bg-info me-1";
        badge.textContent = provision;
        container.appendChild(badge);
    });
}

function updateClauseProvisionButtons() {
    const clauseButton = document.getElementById("clauseButton");
    const provisionButton = document.getElementById("provisionButton");
    
    clauseButton.disabled = state.filters.provisions.length > 0;
    provisionButton.disabled = state.filters.clauses.length > 0;
    
    // Update button text
    const clauseCap = state.filters.mode === "realtime" ? 3 : CLAUSE_KEYS.length;
    const provisionCap = state.filters.mode === "realtime" ? 3 : PROVISION_KEYS.length;
    
    if (state.filters.clauses.length > 0) {
        clauseButton.textContent = `${state.filters.clauses.length} selected (max ${clauseCap})`;
    } else {
        clauseButton.textContent = `Select up to ${clauseCap}`;
    }
    
    if (state.filters.provisions.length > 0) {
        provisionButton.textContent = `${state.filters.provisions.length} selected (max ${provisionCap})`;
    } else {
        provisionButton.textContent = state.filters.mode === "realtime" ? "Select up to 3" : "Select provisions to compare";
    }
}

function updateContractsTable() {
    const tbody = document.getElementById("contractsTableBody");
    const filtered = getFilteredContracts();
    
    tbody.innerHTML = "";
    filtered.forEach(contract => {
        const isSelected = state.picked.includes(contract.id);
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><i class="bi bi-file-text"></i> ${contract.title}</td>
            <td>${contract.counterparty}</td>
            <td>${contract.effective}</td>
            <td><span class="badge bg-${contract.law === 'Delaware' ? 'primary' : 'secondary'}">${contract.law}</span></td>
            <td><span class="badge bg-outline-info">${contract.type}</span></td>
            <td>
                <button class="btn btn-sm ${isSelected ? 'btn-primary' : 'btn-outline-primary'}" 
                        onclick="toggleContractSelection('${contract.id}')">
                    ${isSelected ? 'Selected' : 'Select'}
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="showContractDetails('${contract.id}')">
                    <i class="bi bi-info-circle"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function showContractDetails(contractId) {
    const contract = state.contracts.find(c => c.id === contractId);
    if (!contract) return;
    
    const modal = new bootstrap.Modal(document.getElementById('contractDetailsModal'));
    document.getElementById('contractDetailsTitle').textContent = contract.title;
    
    const body = document.getElementById('contractDetailsBody');
    body.innerHTML = `
        <div class="row">
            ${CLAUSE_KEYS.map(key => `
                <div class="col-md-6 mb-3">
                    <h6>${key}</h6>
                    <p class="text-muted">${highlightText(contract.clauses[key] || '', state.searchText)}</p>
                </div>
            `).join('')}
        </div>
    `;
    
    modal.show();
}

function updateClauseCompare() {
    const container = document.getElementById("clauseCompareContent");
    const pickedContracts = state.contracts.filter(c => state.picked.includes(c.id));
    
    if (pickedContracts.length < 2) {
        container.innerHTML = `
            <div class="alert alert-info">
                Select 2+ contracts to compare clauses.
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="row">
            ${CLAUSE_KEYS.map(key => `
                <div class="col-lg-4 mb-3">
                    <div class="card bg-dark">
                        <div class="card-header">
                            <h6 class="mb-0">${getClauseIcon(key)} ${key}</h6>
                        </div>
                        <div class="card-body">
                            ${pickedContracts.map(contract => `
                                <div class="mb-2 p-2 border rounded">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span class="badge bg-secondary">${contract.id}</span>
                                        <span class="badge bg-info">${contract.law}</span>
                                    </div>
                                    <small>${highlightText(contract.clauses[key] || '', state.searchText)}</small>
                                </div>
                            `).join('')}
                            <small class="text-muted">Inline highlights show exact wording differences.</small>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
        <button class="btn btn-outline-primary" onclick="showRawDiff()">
            <i class="bi bi-arrows-angle-expand"></i> Show Raw Diff
        </button>
    `;
}

function updateProvisionCompare() {
    const container = document.getElementById("provisionCompareContent");
    const pickedContracts = state.contracts.filter(c => state.picked.includes(c.id));
    const provisions = state.filters.provisions.length ? state.filters.provisions : ["Payment Terms", "Insurance"];
    
    if (pickedContracts.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                Select contracts and provisions to compare against gold standard.
            </div>
        `;
        return;
    }
    
    // Create comparison table
    let tableHTML = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Contract</th>
                        <th>Law</th>
                        ${provisions.map(p => `<th>${p}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;
    
    pickedContracts.forEach(contract => {
        tableHTML += `
            <tr>
                <td>${contract.id}</td>
                <td><span class="badge bg-secondary">${contract.law}</span></td>
                ${provisions.map(p => {
                    const value = contract.clauses[p] || '—';
                    const goldStandard = GOLD_STANDARD[p];
                    const isDifferent = goldStandard && normalizeText(value) !== normalizeText(goldStandard);
                    return `
                        <td class="${isDifferent ? 'bg-warning bg-opacity-25' : ''}">
                            ${value}
                            ${isDifferent ? '<span class="badge bg-warning ms-1">Δ</span>' : ''}
                            ${!goldStandard ? '<span class="badge bg-secondary ms-1">No GS</span>' : ''}
                        </td>
                    `;
                }).join('')}
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
        </div>
        <small class="text-muted">Δ indicates difference from gold standard (C-002)</small>
    `;
    
    container.innerHTML = tableHTML;
}

function updateJurisdictionInsights() {
    const container = document.getElementById("jurisdictionBadges");
    const jurisdictionCounts = {};
    
    state.contracts.forEach(contract => {
        jurisdictionCounts[contract.law] = (jurisdictionCounts[contract.law] || 0) + 1;
    });
    
    const sorted = Object.entries(jurisdictionCounts).sort((a, b) => b[1] - a[1]);
    
    container.innerHTML = "";
    sorted.forEach(([law, count]) => {
        const badge = document.createElement("span");
        badge.className = "badge bg-secondary me-1";
        badge.textContent = `${law} · ${count}`;
        container.appendChild(badge);
    });
}

function applyFilters() {
    updateContractsTable();
    updateClauseCompare();
    updateProvisionCompare();
}

async function getAnswer() {
    const answerText = document.getElementById("answerText");
    
    // Show loading state
    answerText.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing query...';
    
    try {
        // Call API to get answer
        const response = await fetch('/api/contract_query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: state.question,
                filters: state.filters,
                selected_contracts: state.picked
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            answerText.innerHTML = data.answer || 'No answer available.';
        } else {
            // Fallback to mock answer
            const nonDelawareContracts = state.contracts
                .filter(c => c.law !== "Delaware")
                .map(c => c.id)
                .join(", ");
            
            answerText.innerHTML = `
                Contracts governed by states other than Delaware: <span class="badge bg-secondary">${nonDelawareContracts || "—"}</span>. 
                The most divergent indemnity language appears in <span class="badge bg-info">C-003</span> (bodily injury/property focus) 
                vs <span class="badge bg-info">C-002</span> (IP infringement focus).
            `;
        }
    } catch (error) {
        console.error('Error getting answer:', error);
        // Use mock answer as fallback
        const nonDelawareContracts = state.contracts
            .filter(c => c.law !== "Delaware")
            .map(c => c.id)
            .join(", ");
        
        answerText.innerHTML = `
            Contracts governed by states other than Delaware: <span class="badge bg-secondary">${nonDelawareContracts || "—"}</span>. 
            The most divergent indemnity language appears in <span class="badge bg-info">C-003</span> (bodily injury/property focus) 
            vs <span class="badge bg-info">C-002</span> (IP infringement focus).
        `;
    }
}

function compareSelected() {
    if (state.picked.length < 2) {
        alert("Please select at least 2 contracts to compare.");
        return;
    }
    
    // Switch to appropriate tab based on filters
    if (state.filters.clauses.length > 0) {
        document.querySelector('[href="#clausesTab"]').click();
        updateClauseCompare();
    } else if (state.filters.provisions.length > 0) {
        document.querySelector('[href="#provisionsTab"]').click();
        updateProvisionCompare();
    } else {
        // Default to clause compare
        document.querySelector('[href="#clausesTab"]').click();
        updateClauseCompare();
    }
}

function copyResults() {
    const pickedContracts = state.contracts.filter(c => state.picked.includes(c.id));
    const results = {
        query: state.question,
        filters: state.filters,
        selected_contracts: pickedContracts,
        timestamp: new Date().toISOString()
    };
    
    navigator.clipboard.writeText(JSON.stringify(results, null, 2))
        .then(() => {
            // Show success feedback
            const btn = document.getElementById("copyResults");
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check"></i> Copied!';
            setTimeout(() => {
                btn.innerHTML = originalHTML;
            }, 2000);
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy results to clipboard');
        });
}

function showRawDiff() {
    const pickedContracts = state.contracts.filter(c => state.picked.includes(c.id));
    if (pickedContracts.length < 2) return;
    
    const modal = new bootstrap.Modal(document.getElementById('rawDiffModal'));
    const body = document.getElementById('rawDiffBody');
    
    body.innerHTML = `
        <div class="row">
            ${pickedContracts.slice(0, -1).map((contract1, i) => {
                const contract2 = pickedContracts[i + 1];
                return CLAUSE_KEYS.map(key => `
                    <div class="col-md-6 mb-3">
                        <h6>${contract1.id} vs ${contract2.id} - ${key}</h6>
                        <div class="border rounded p-2">
                            ${diffStrings(contract1.clauses[key] || '', contract2.clauses[key] || '')}
                        </div>
                    </div>
                `).join('');
            }).join('')}
        </div>
    `;
    
    modal.show();
}

// Helper functions
function highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, 'ig');
    return text.replace(regex, '<mark>$1</mark>');
}

function normalizeText(text) {
    return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function diffStrings(a, b) {
    const aWords = a.split(/\s+/);
    const bWords = new Set(b.split(/\s+/));
    
    return aWords.map(word => {
        if (bWords.has(word)) {
            return `<span>${word}</span>`;
        } else {
            return `<span class="bg-warning bg-opacity-25">${word}</span>`;
        }
    }).join(' ');
}

function getClauseIcon(clauseName) {
    const icons = {
        "Indemnity": '<i class="bi bi-shield"></i>',
        "Payment Terms": '<i class="bi bi-cash"></i>',
        "Governing Law": '<i class="bi bi-balance-scale"></i>',
        "Insurance": '<i class="bi bi-umbrella"></i>',
        "Limitation of Liability": '<i class="bi bi-exclamation-triangle"></i>'
    };
    return icons[clauseName] || '<i class="bi bi-file-text"></i>';
}

// Tab change listeners
document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener('shown.bs.tab', function (e) {
        const target = e.target.getAttribute('href');
        if (target === '#clausesTab') {
            updateClauseCompare();
        } else if (target === '#provisionsTab') {
            updateProvisionCompare();
        }
    });
});