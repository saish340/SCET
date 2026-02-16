/**
 * SCET Frontend Application
 * Copyright Status Tag - JavaScript
 * Version 3.0 - Cache Bust Version
 */

// Configuration
// For local development use localhost, for production use relative path
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';  // Same domain on Vercel

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const contentType = document.getElementById('contentType');
const jurisdiction = document.getElementById('jurisdiction');
const metadataSource = document.getElementById('metadataSource');
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
    hideElements([searchResults, smartTagSection, suggestions]);
    
    try {
        // Build query parameters
        const params = new URLSearchParams({
            q: query,
            jurisdiction: jurisdiction.value || 'US',
            type: contentType.value || '',
            source: metadataSource.value || ''
        });
        
        // Fetch search results
        const response = await fetch(`${API_BASE}/search?${params}`);
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        currentSearchId = Math.random().toString(36).substr(2, 9);
        
        displaySearchResults(data);
        
    } catch (error) {
        console.error('Search error:', error);
        displayError('Search failed. Please check your connection and try again.');
    } finally {
        hideLoading();
    }
}

// Display Search Results
function displaySearchResults(data) {
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
    div.className = 'result-card';
    div.onclick = () => selectResult(result);
    
    const statusClass = result.copyright_status.toLowerCase().replace(' ', '_');
    const statusBadgeClass = result.copyright_status === 'PROTECTED' ? 'badge-protected' : 
                             result.copyright_status === 'PUBLIC_DOMAIN' ? 'badge-public' : 
                             'badge-unknown';
    
    div.innerHTML = `
        <div class="result-header">
            <div>
                <div class="result-title">${escapeHtml(result.title)}</div>
                ${result.creator ? `<div class="result-creator">By ${escapeHtml(result.creator)}</div>` : ''}
            </div>
        </div>
        <div class="result-meta">
            ${result.publication_year ? `<span class="result-year">📅 ${result.publication_year}</span>` : ''}
            ${result.content_type ? `<span class="result-type">📑 ${capitalizeFirst(result.content_type)}</span>` : ''}
            ${result.source ? `<span class="result-source">📚 ${escapeHtml(result.source)}</span>` : ''}
            <span class="result-badge ${statusBadgeClass}">${formatStatus(result.copyright_status)}</span>
            <span class="similarity-score">🎯 ${Math.round(result.similarity_score * 100)}% match</span>
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
    
    // Add fallbacks for missing fields from API
    const statusColor = tag.status_color || (tag.status === 'PUBLIC_DOMAIN' ? 'green' : 'red');
    const statusEmoji = tag.status_emoji || tag.emoji || '📋';
    const statusText = tag.status_text || (tag.status === 'PUBLIC_DOMAIN' ? 'Public Domain' : 'Copyright Protected');
    const expiryTimeline = tag.expiry_timeline || tag.expiry_info || 'Unknown';
    const allowedUsesSummary = tag.allowed_uses_summary || tag.allowed_uses || [];
    const confidenceLevel = tag.confidence_level || (tag.confidence >= 0.8 ? 'High' : 'Medium');
    const confidenceScore = tag.confidence_score || tag.confidence || 0.8;
    const tagDisclaimer = tag.disclaimer || 'This analysis is for informational purposes only.';
    const generatedAt = tag.generated_at || new Date().toISOString();
    const tagVersion = tag.tag_version || '1.0';
    
    const colorClass = `status-${statusColor}`;
    
    // Build recommendations HTML with fallbacks
    const recommendationsHtml = data.recommendations.map(rec => `
        <div class="recommendation-item ${rec.type || 'info'}">
            <span class="rec-icon">${rec.icon}</span>
            <div class="rec-content">
                <strong>${rec.title || 'Recommendation'}</strong>
                <p>${rec.description || rec.text || ''}</p>
            </div>
        </div>
    `).join('');
    
    // Build risk assessment HTML with fallbacks
    const risk = data.risk_assessment;
    const riskColor = risk.color || (risk.level === 'low' || risk.level === 'Low' ? '#28a745' : '#ffc107');
    const riskIcon = risk.icon || (risk.level === 'low' || risk.level === 'Low' ? '✅' : '⚠️');
    const riskDesc = risk.description || `Risk level: ${risk.level}`;
    const riskHtml = `
        <div class="risk-assessment" style="border-left: 4px solid ${riskColor}">
            <div class="risk-header">
                <span class="risk-icon">${riskIcon}</span>
                <span class="risk-level" style="color: ${riskColor}">${risk.level} Risk</span>
            </div>
            <p class="risk-description">${riskDesc}</p>
            <div class="risk-details">
                <span>📊 Commercial: ${risk.commercial_risk || 'Unknown'}</span>
                <span>👤 Personal: ${risk.personal_risk || 'Unknown'}</span>
            </div>
        </div>
    `;
    
    // Build legal checklist HTML with fallbacks
    const checklistHtml = data.legal_checklist.map(item => `
        <div class="checklist-item ${item.status || (item.checked ? 'done' : 'pending')}">
            <span class="check-icon">${item.required !== false ? '☐' : '○'}</span>
            <span class="check-text">${item.item}</span>
            <span class="check-status">${item.status || (item.checked ? 'done' : 'pending')}</span>
        </div>
    `).join('');
    
    // Build quick actions HTML
    const actionsHtml = data.quick_actions.map(action => `
        <button class="quick-action-btn" onclick="handleQuickAction('${action.action}', '${escapeHtml(tag.title)}')">${action.label}</button>
    `).join('');
    
    smartTagContainer.innerHTML = `
        <div class="smart-tag ${colorClass}">
            <div class="tag-header">
                <span class="tag-emoji">${statusEmoji}</span>
                <span class="tag-status" style="color: var(--${getColorVar(statusColor)}-color)">
                    ${statusText}
                </span>
            </div>
            
            <div class="tag-title">${escapeHtml(tag.title)}</div>
            ${tag.creator ? `<div class="tag-creator">By ${escapeHtml(tag.creator)}</div>` : ''}
            ${tag.publication_year ? `<div class="tag-year">Published: ${tag.publication_year}</div>` : ''}
            
            <div class="tag-timeline">
                <span>⏱</span>
                <span>${escapeHtml(expiryTimeline)}</span>
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
                    ${allowedUsesSummary.map(use => {
                        const isAllowed = use.startsWith('✓') || use.startsWith('✅');
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
                <span>🎯 Confidence: ${confidenceLevel} (${Math.round(confidenceScore * 100)}%)</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidenceScore * 100}%; background: ${getConfidenceColor(confidenceScore)}"></div>
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
                ⚠️ ${escapeHtml(tagDisclaimer)}
            </div>
            
            <div class="tag-meta">
                <span>Generated: ${new Date(generatedAt).toLocaleDateString()}</span>
                <span>SCET v${tagVersion} | ${tag.jurisdiction}</span>
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
    console.log('SCET Frontend loaded - v3.0');
    
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
    'Harry Potter',
    'Sherlock Holmes',
    'The Great Gatsby'
];

// Add example searches hint
const searchHint = document.createElement('div');
searchHint.className = 'search-hint';
searchHint.style.cssText = 'font-size: 13px; color: var(--gray-500); margin-top: 8px;';
searchHint.innerHTML = `Try: ${examples.map(e => `<a href="#" style="color: var(--primary-color);" onclick="document.getElementById('searchInput').value='${e}';performSearch();return false;">${e}</a>`).join(' • ')}`;
document.querySelector('.search-box').appendChild(searchHint);
