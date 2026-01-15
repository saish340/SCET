/**
 * SCET Frontend Application
 * Smart Copyright Expiry Tag - JavaScript
 */

// Configuration
// For local development use localhost, for production use your deployed backend URL
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api/v1'
    : 'https://your-backend-url.onrender.com/api/v1';  // Update this after deploying backend

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const contentType = document.getElementById('contentType');
const jurisdiction = document.getElementById('jurisdiction');
const correctionNotice = document.getElementById('correctionNotice');
const correctedQuery = document.getElementById('correctedQuery');
const loadingIndicator = document.getElementById('loadingIndicator');
const aiExplanation = document.getElementById('aiExplanation');
const aiExplanationText = document.getElementById('aiExplanationText');
const searchResults = document.getElementById('searchResults');
const resultsList = document.getElementById('resultsList');
const suggestions = document.getElementById('suggestions');
const suggestionsList = document.getElementById('suggestionsList');
const smartTagSection = document.getElementById('smartTagSection');
const smartTagContainer = document.getElementById('smartTagContainer');

// State
let currentSearchId = null;
let selectedWorkId = null;

// Event Listeners
searchBtn.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

correctedQuery.addEventListener('click', (e) => {
    e.preventDefault();
    searchInput.value = correctedQuery.textContent;
    performSearch();
});

// Main Search Function
async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;
    
    showLoading();
    hideElements([correctionNotice, aiExplanation, searchResults, suggestions, smartTagSection]);
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                content_type: contentType.value || null,
                max_results: 10,
                include_similar: true
            })
        });
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        displaySearchResults(data);
        
    } catch (error) {
        console.error('Search error:', error);
        displayError('Search failed. Please try again.');
    } finally {
        hideLoading();
    }
}

// Display Search Results
function displaySearchResults(data) {
    // Show correction notice if query was corrected
    if (data.corrected_query) {
        correctedQuery.textContent = data.corrected_query;
        correctionNotice.classList.remove('hidden');
    }
    
    // Show AI explanation
    if (data.ai_explanation) {
        aiExplanationText.textContent = data.ai_explanation;
        aiExplanation.classList.remove('hidden');
    }
    
    // Show results
    if (data.results && data.results.length > 0) {
        resultsList.innerHTML = '';
        
        data.results.forEach(result => {
            const resultEl = createResultElement(result);
            resultsList.appendChild(resultEl);
        });
        
        searchResults.classList.remove('hidden');
    } else {
        resultsList.innerHTML = '<p class="no-results">No results found. Try a different search term.</p>';
        searchResults.classList.remove('hidden');
    }
    
    // Show suggestions
    if (data.suggestions && data.suggestions.length > 0) {
        suggestionsList.innerHTML = '';
        
        data.suggestions.forEach(suggestion => {
            const tag = document.createElement('span');
            tag.className = 'suggestion-tag';
            tag.textContent = suggestion;
            tag.addEventListener('click', () => {
                searchInput.value = suggestion;
                performSearch();
            });
            suggestionsList.appendChild(tag);
        });
        
        suggestions.classList.remove('hidden');
    }
}

// Create Result Element
function createResultElement(result) {
    const div = document.createElement('div');
    div.className = 'result-item';
    div.onclick = () => selectResult(result);
    
    const statusClass = result.copyright_status.toLowerCase().replace(' ', '_');
    
    div.innerHTML = `
        <div class="result-info">
            <div class="result-title">${escapeHtml(result.title)}</div>
            <div class="result-meta">
                ${result.creator ? `By ${escapeHtml(result.creator)} • ` : ''}
                ${result.publication_year ? `${result.publication_year} • ` : ''}
                ${result.content_type ? capitalizeFirst(result.content_type) : 'Unknown type'}
                ${result.source ? ` • Source: ${escapeHtml(result.source)}` : ''}
            </div>
        </div>
        <div class="result-score">
            <span class="score-badge">${Math.round(result.similarity_score * 100)}% match</span>
            <span class="status-badge ${statusClass}">${formatStatus(result.copyright_status)}</span>
        </div>
    `;
    
    return div;
}

// Select a Result and Generate Smart Tag
async function selectResult(result) {
    selectedWorkId = result.id;
    
    showLoading();
    
    try {
        // Use the detailed endpoint for richer output
        const params = new URLSearchParams({
            title: result.title,
            creator: result.creator || '',
            year: result.publication_year || '',
            type: result.content_type || '',
            jurisdiction: jurisdiction.value || 'US'
        });
        
        const response = await fetch(`${API_BASE}/tag/detailed?${params}`);
        
        if (!response.ok) {
            throw new Error('Failed to generate tag');
        }
        
        const detailedTag = await response.json();
        displayDetailedSmartTag(detailedTag);
        
    } catch (error) {
        console.error('Tag generation error:', error);
        displayError('Failed to generate Smart Tag. Please try again.');
    } finally {
        hideLoading();
    }
}

// Display Enhanced Smart Tag with Recommendations
function displayDetailedSmartTag(data) {
    const tag = data.tag;
    const colorClass = `status-${tag.status_color}`;
    
    // Build recommendations HTML
    const recommendationsHtml = data.recommendations.map(rec => `
        <div class="recommendation-item ${rec.type}">
            <span class="rec-icon">${rec.icon}</span>
            <div class="rec-content">
                <strong>${rec.title}</strong>
                <p>${rec.description}</p>
            </div>
        </div>
    `).join('');
    
    // Build risk assessment HTML
    const risk = data.risk_assessment;
    const riskHtml = `
        <div class="risk-assessment" style="border-left: 4px solid ${risk.color}">
            <div class="risk-header">
                <span class="risk-icon">${risk.icon}</span>
                <span class="risk-level" style="color: ${risk.color}">${risk.level} Risk</span>
            </div>
            <p class="risk-description">${risk.description}</p>
            <div class="risk-details">
                <span>📊 Commercial: ${risk.commercial_risk}</span>
                <span>👤 Personal: ${risk.personal_risk}</span>
            </div>
        </div>
    `;
    
    // Build legal checklist HTML
    const checklistHtml = data.legal_checklist.map(item => `
        <div class="checklist-item ${item.status}">
            <span class="check-icon">${item.required ? '☐' : '○'}</span>
            <span class="check-text">${item.item}</span>
            <span class="check-status">${item.status}</span>
        </div>
    `).join('');
    
    // Build quick actions HTML
    const actionsHtml = data.quick_actions.map(action => `
        <button class="quick-action-btn" onclick="handleQuickAction('${action.action}', '${escapeHtml(tag.title)}')">${action.label}</button>
    `).join('');
    
    smartTagContainer.innerHTML = `
        <div class="smart-tag ${colorClass}">
            <div class="tag-header">
                <span class="tag-emoji">${tag.status_emoji}</span>
                <span class="tag-status" style="color: var(--${getColorVar(tag.status_color)}-color)">
                    ${tag.status_text}
                </span>
            </div>
            
            <div class="tag-title">${escapeHtml(tag.title)}</div>
            ${tag.creator ? `<div class="tag-creator">By ${escapeHtml(tag.creator)}</div>` : ''}
            ${tag.publication_year ? `<div class="tag-year">Published: ${tag.publication_year}</div>` : ''}
            
            <div class="tag-timeline">
                <span>⏱</span>
                <span>${escapeHtml(tag.expiry_timeline)}</span>
            </div>
            
            <!-- Summary Section -->
            <div class="tag-summary">
                <p>${data.summary}</p>
            </div>
            
            <!-- Risk Assessment -->
            <div class="tag-section">
                <h4>⚖️ Risk Assessment</h4>
                ${riskHtml}
            </div>
            
            <!-- Allowed Uses -->
            <div class="tag-uses">
                <h4>📋 Allowed Uses</h4>
                <div class="uses-list">
                    ${tag.allowed_uses_summary.map(use => {
                        const isAllowed = use.startsWith('✓');
                        return `<span class="use-item ${isAllowed ? 'allowed' : 'denied'}">${escapeHtml(use)}</span>`;
                    }).join('')}
                </div>
            </div>
            
            <!-- Recommendations -->
            <div class="tag-section">
                <h4>💡 Recommendations</h4>
                <div class="recommendations-list">
                    ${recommendationsHtml}
                </div>
            </div>
            
            <!-- Legal Checklist -->
            <div class="tag-section">
                <h4>✅ Legal Checklist</h4>
                <div class="legal-checklist">
                    ${checklistHtml}
                </div>
            </div>
            
            <!-- Confidence -->
            <div class="tag-confidence">
                <span>🎯 Confidence: ${tag.confidence_level} (${Math.round(tag.confidence_score * 100)}%)</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${tag.confidence_score * 100}%; background: ${getConfidenceColor(tag.confidence_score)}"></div>
                </div>
            </div>
            
            ${tag.ai_reasoning ? `
            <div class="tag-reasoning">
                <div class="tag-reasoning-title">
                    <span>🤖</span>
                    AI Analysis
                </div>
                <p>${escapeHtml(tag.ai_reasoning)}</p>
            </div>
            ` : ''}
            
            <!-- Quick Actions -->
            <div class="tag-actions">
                ${actionsHtml}
            </div>
            
            <div class="tag-disclaimer">
                ⚠️ ${escapeHtml(tag.disclaimer)}
            </div>
            
            <div class="tag-meta">
                <span>Generated: ${new Date(tag.generated_at).toLocaleDateString()}</span>
                <span>SCET v${tag.tag_version} | ${tag.jurisdiction}</span>
            </div>
        </div>
    `;
    
    smartTagSection.classList.remove('hidden');
    smartTagSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Legacy display function for backward compatibility
function displaySmartTag(tag) {
    displayDetailedSmartTag({
        tag: tag,
        recommendations: [],
        quick_actions: [],
        risk_assessment: { level: "Unknown", color: "#6c757d", icon: "❓", description: "Risk not assessed" },
        summary: "",
        legal_checklist: []
    });
}

// Handle quick action button clicks
function handleQuickAction(action, title) {
    switch(action) {
        case 'download':
            downloadTag(title);
            break;
        case 'share':
            shareTag(title);
            break;
        case 'copy_citation':
            copyCitation(title);
            break;
        case 'full_report':
            window.open(`${API_BASE}/tag/html?title=${encodeURIComponent(title)}`, '_blank');
            break;
        default:
            alert(`Action "${action}" - Coming soon!`);
    }
}

function downloadTag(title) {
    alert(`Download tag for "${title}" - Feature coming soon!`);
}

function shareTag(title) {
    if (navigator.share) {
        navigator.share({
            title: `Copyright Status: ${title}`,
            text: `Check the copyright status of "${title}" on SCET`,
            url: window.location.href
        });
    } else {
        navigator.clipboard.writeText(window.location.href);
        alert('Link copied to clipboard!');
    }
}

function copyCitation(title) {
    const citation = `Copyright analysis for "${title}" generated by SCET - Smart Copyright Expiry Tag System. ${new Date().toLocaleDateString()}`;
    navigator.clipboard.writeText(citation);
    alert('Citation copied to clipboard!');
}

function getConfidenceColor(score) {
    if (score >= 0.8) return '#28a745';
    if (score >= 0.6) return '#ffc107';
    if (score >= 0.4) return '#fd7e14';
    return '#dc3545';
}

// Utility Functions
function showLoading() {
    loadingIndicator.classList.remove('hidden');
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function hideElements(elements) {
    elements.forEach(el => el.classList.add('hidden'));
}

function displayError(message) {
    resultsList.innerHTML = `<p class="error-message" style="color: var(--danger-color); text-align: center; padding: 20px;">${message}</p>`;
    searchResults.classList.remove('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatStatus(status) {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getColorVar(color) {
    const colorMap = {
        'green': 'success',
        'yellow': 'warning',
        'orange': 'warning',
        'red': 'danger',
        'gray': 'gray-500'
    };
    return colorMap[color] || 'gray-500';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('SCET Frontend loaded');
    
    // Focus search input
    searchInput.focus();
    
    // Check API health
    checkApiHealth();
});

async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            console.log('API connected:', data);
        } else {
            console.warn('API degraded:', data);
        }
    } catch (error) {
        console.warn('API not reachable. Make sure backend is running.');
    }
}

// Demo: Quick search examples
const examples = [
    'Pride and Prejudice',
    'Harry Potter',
    'Symphony No. 5',
    'Romeo and Juliet',
    'The Great Gatsby'
];

// Add example searches hint
const searchHint = document.createElement('div');
searchHint.className = 'search-hint';
searchHint.style.cssText = 'font-size: 13px; color: var(--gray-500); margin-top: 8px;';
searchHint.innerHTML = `Try: ${examples.map(e => `<a href="#" style="color: var(--primary-color);" onclick="document.getElementById('searchInput').value='${e}';performSearch();return false;">${e}</a>`).join(' • ')}`;
document.querySelector('.search-box').appendChild(searchHint);
