/**
 * SCET Frontend Application
 * Copyright Status Tag - JavaScript
 * Version 4.0 - Search, report, and history enhancements
 */

const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';

const STORAGE_KEYS = {
    lastReport: 'scet:last-report',
    recentReports: 'scet:recent-reports'
};

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
const recentReports = document.getElementById('recentReports');

let currentSearchId = null;
let selectedWorkId = null;
let selectedResultData = null;
let latestDetailedTagData = null;

const isHomePage = window.location.pathname === '/' || window.location.pathname.endsWith('index.html');
const isSearchPage = window.location.pathname.endsWith('search.html');
const REPORT_PAGE_PATH = window.location.hostname === 'localhost' ? 'report.html' : '/report';

if (searchBtn) {
    searchBtn.addEventListener('click', performSearch);
}

if (searchInput) {
    searchInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            performSearch();
        }
    });
}

if (correctedQuery) {
    correctedQuery.addEventListener('click', (event) => {
        event.preventDefault();
        searchInput.value = correctedQuery.textContent;
        performSearch();
    });
}

async function performSearch() {
    const query = (searchInput && searchInput.value.trim()) || '';
    if (!query) {
        return;
    }

    if (isHomePage) {
        const params = new URLSearchParams({
            query,
            type: (contentType && contentType.value) || '',
            country: (jurisdiction && jurisdiction.value) || '',
            source: (metadataSource && metadataSource.value) || ''
        });
        window.location.href = `search.html?${params.toString()}`;
        return;
    }

    showLoading();
    hideElements([searchResults, smartTagSection, suggestions, correctionNotice, aiExplanation]);

    try {
        const params = new URLSearchParams({
            q: query,
            jurisdiction: (jurisdiction && jurisdiction.value) || 'US',
            type: (contentType && contentType.value) || '',
            source: (metadataSource && metadataSource.value) || ''
        });

        const response = await fetch(`${API_BASE}/search?${params.toString()}`);
        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();
        currentSearchId = Math.random().toString(36).slice(2, 11);
        displaySearchResults(data);
    } catch (error) {
        console.error('Search error:', error);
        displayError('Search failed. Please check your connection and try again.');
    } finally {
        hideLoading();
    }
}

function displaySearchResults(data) {
    renderCorrection(data.correction);
    renderAiExplanation(data);

    if (data.results && data.results.length > 0) {
        resultsList.innerHTML = '';
        data.results.forEach((result) => {
            resultsList.appendChild(createResultElement(result));
        });
        searchResults.classList.remove('hidden');
    } else {
        const fallbackNote = data.filter_applied && data.fallback_to_broad_results
            ? 'No exact matches for this content type, so SCET is showing the closest broader matches.'
            : 'No results found. Try a different search term.';
        resultsList.innerHTML = `<p class="no-results">${escapeHtml(fallbackNote)}</p>`;
        searchResults.classList.remove('hidden');
    }

    renderSuggestions(data.suggestions || []);
}

function renderCorrection(correction) {
    if (!correction || !correctionNotice || !correctedQuery) {
        return;
    }
    correctedQuery.textContent = correction;
    correctionNotice.classList.remove('hidden');
}

function renderAiExplanation(data) {
    if (!aiExplanation || !aiExplanationText) {
        return;
    }

    const parts = [];
    if (data.ai_explanation) {
        parts.push(data.ai_explanation);
    }
    if (data.filter_applied && data.fallback_to_broad_results) {
        parts.push('No exact type-specific matches were found, so broader close matches are shown below.');
    }
    if (data.total_results) {
        parts.push(`Showing ${data.total_results} result${data.total_results === 1 ? '' : 's'}.`);
    }

    if (parts.length) {
        aiExplanationText.textContent = parts.join(' ');
        aiExplanation.classList.remove('hidden');
    }
}

function renderSuggestions(items) {
    if (!suggestions || !suggestionsList) {
        return;
    }

    suggestionsList.innerHTML = '';
    if (!items.length) {
        suggestions.classList.add('hidden');
        return;
    }

    items.forEach((suggestion) => {
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

function createResultElement(result) {
    const div = document.createElement('div');
    div.className = 'result-card';
    div.onclick = () => selectResult(result);

    const status = String(result.copyright_status || 'UNKNOWN').toUpperCase();
    const statusBadgeClass = status === 'PROTECTED'
        ? 'badge-protected'
        : status === 'PUBLIC_DOMAIN'
            ? 'badge-public'
            : 'badge-unknown';

    div.innerHTML = `
        <div class="result-header">
            <div>
                <div class="result-title">${escapeHtml(result.title)}</div>
                ${result.creator ? `<div class="result-creator">By ${escapeHtml(result.creator)}</div>` : ''}
            </div>
        </div>
        <div class="result-meta">
            ${result.publication_year ? `<span class="result-year">📅 ${escapeHtml(String(result.publication_year))}</span>` : ''}
            ${result.content_type ? `<span class="result-type">📑 ${escapeHtml(prettyType(result.content_type))}</span>` : ''}
            ${result.source ? `<span class="result-source">📚 ${escapeHtml(result.source)}</span>` : ''}
            <span class="result-badge ${statusBadgeClass}">${escapeHtml(formatStatus(status))}</span>
            <span class="similarity-score">🎯 ${Math.round((result.similarity_score || 0) * 100)}% match</span>
        </div>
    `;

    return div;
}

async function selectResult(result) {
    selectedWorkId = result.id;
    selectedResultData = result;

    showLoading();

    try {
        const params = new URLSearchParams({
            title: result.title,
            creator: result.creator || '',
            year: result.publication_year || '',
            type: result.content_type || '',
            jurisdiction: (jurisdiction && jurisdiction.value) || 'US'
        });

        const response = await fetch(`${API_BASE}/tag/detailed?${params.toString()}`);
        if (!response.ok) {
            throw new Error('Failed to generate tag');
        }

        const detailedTag = await response.json();
        latestDetailedTagData = detailedTag;
        persistRecentReport(buildReportPayload());
        renderRecentReports();
        displayDetailedSmartTag(detailedTag);
    } catch (error) {
        console.error('Tag generation error:', error);
        displayError('Failed to generate Smart Tag. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayDetailedSmartTag(data) {
    const tag = data.tag || {};
    const statusColor = tag.status_color || (tag.status === 'PUBLIC_DOMAIN' ? 'green' : 'red');
    const statusEmoji = tag.status_emoji || tag.emoji || '📋';
    const statusText = tag.status_text || (tag.status === 'PUBLIC_DOMAIN' ? 'Public Domain' : 'Copyright Protected');
    const expiryTimeline = tag.expiry_timeline || tag.expiry_info || 'Unknown';
    const allowedUsesSummary = tag.allowed_uses_summary || tag.allowed_uses || [];
    const confidenceScore = Number(tag.confidence_score || tag.confidence || 0.8);
    const confidenceLevel = tag.confidence_level || (confidenceScore >= 0.8 ? 'High' : confidenceScore >= 0.6 ? 'Medium' : 'Low');
    const tagDisclaimer = tag.disclaimer || 'This analysis is for informational purposes only.';
    const generatedAt = tag.generated_at || new Date().toISOString();
    const tagVersion = tag.tag_version || '1.0';
    const colorClass = `status-${statusColor}`;

    const recommendationsHtml = (data.recommendations || []).map((rec) => `
        <div class="recommendation-item ${rec.type || 'info'}">
            <span class="rec-icon">${escapeHtml(rec.icon || 'ℹ️')}</span>
            <div class="rec-content">
                <strong>${escapeHtml(rec.title || 'Recommendation')}</strong>
                <p>${escapeHtml(rec.description || rec.text || '')}</p>
            </div>
        </div>
    `).join('');

    const risk = data.risk_assessment || {};
    const riskColor = risk.color || ((risk.level || '').toLowerCase() === 'low' ? '#28a745' : '#ffc107');
    const riskIcon = risk.icon || ((risk.level || '').toLowerCase() === 'low' ? '✅' : '⚠️');
    const riskHtml = `
        <div class="risk-assessment" style="border-left: 4px solid ${riskColor}">
            <div class="risk-header">
                <span class="risk-icon">${escapeHtml(riskIcon)}</span>
                <span class="risk-level" style="color: ${riskColor}">${escapeHtml(risk.level || 'Unknown')} Risk</span>
            </div>
            <p class="risk-description">${escapeHtml(risk.description || 'Risk level not assessed.')}</p>
            <div class="risk-details">
                <span>📊 Commercial: ${escapeHtml(risk.commercial_risk || 'Unknown')}</span>
                <span>👤 Personal: ${escapeHtml(risk.personal_risk || 'Unknown')}</span>
            </div>
        </div>
    `;

    const checklistHtml = (data.legal_checklist || []).map((item) => `
        <div class="checklist-item ${item.status || (item.checked ? 'done' : 'pending')}">
            <span class="check-icon">${item.required !== false ? '☐' : '○'}</span>
            <span class="check-text">${escapeHtml(item.item || '')}</span>
            <span class="check-status">${escapeHtml(item.status || (item.checked ? 'done' : 'pending'))}</span>
        </div>
    `).join('');

    const actionsHtml = (data.quick_actions || []).map((action) => `
        <button class="quick-action-btn" data-action="${escapeHtml(action.action)}">${escapeHtml(action.label)}</button>
    `).join('');

    smartTagContainer.innerHTML = `
        <div class="smart-tag ${colorClass}">
            <div class="tag-header">
                <span class="tag-emoji">${statusEmoji}</span>
                <span class="tag-status" style="color: var(--${getColorVar(statusColor)}-color)">
                    ${escapeHtml(statusText)}
                </span>
            </div>

            <div class="tag-title">${escapeHtml(tag.title || 'Unknown')}</div>
            ${tag.creator ? `<div class="tag-creator">By ${escapeHtml(tag.creator)}</div>` : ''}
            ${tag.publication_year ? `<div class="tag-year">Published: ${escapeHtml(String(tag.publication_year))}</div>` : ''}

            <div class="tag-timeline">
                <span>⏱</span>
                <span>${escapeHtml(expiryTimeline)}</span>
            </div>

            <div class="tag-summary">
                <p>${escapeHtml(data.summary || '')}</p>
            </div>

            <div class="tag-section">
                <h4>⚖️ Risk Assessment</h4>
                ${riskHtml}
            </div>

            <div class="tag-uses">
                <h4>📋 Allowed Uses</h4>
                <div class="uses-list">
                    ${allowedUsesSummary.map((use) => {
                        const isAllowed = use.startsWith('✓') || use.startsWith('✅');
                        return `<span class="use-item ${isAllowed ? 'allowed' : 'denied'}">${escapeHtml(use)}</span>`;
                    }).join('')}
                </div>
            </div>

            <div class="tag-section">
                <h4>💡 Recommendations</h4>
                <div class="recommendations-list">${recommendationsHtml}</div>
            </div>

            <div class="tag-section">
                <h4>✅ Legal Checklist</h4>
                <div class="legal-checklist">${checklistHtml}</div>
            </div>

            <div class="tag-confidence">
                <span>🎯 Confidence: ${escapeHtml(confidenceLevel)} (${Math.round(confidenceScore * 100)}%)</span>
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
            </div>` : ''}

            <div class="tag-actions">${actionsHtml}</div>

            <div class="tag-disclaimer">⚠️ ${escapeHtml(tagDisclaimer)}</div>

            <div class="tag-meta">
                <span>Generated: ${new Date(generatedAt).toLocaleDateString()}</span>
                <span>SCET v${escapeHtml(tagVersion)} | ${escapeHtml(tag.jurisdiction || 'US')}</span>
            </div>
        </div>
    `;

    smartTagContainer.querySelectorAll('[data-action]').forEach((button) => {
        button.addEventListener('click', () => {
            handleQuickAction(button.dataset.action, tag.title || '');
        });
    });

    smartTagSection.classList.remove('hidden');
    smartTagSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displaySmartTag(tag) {
    displayDetailedSmartTag({
        tag,
        recommendations: [],
        quick_actions: [],
        risk_assessment: { level: 'Unknown', color: '#6c757d', icon: '❓', description: 'Risk not assessed' },
        summary: '',
        legal_checklist: []
    });
}

function handleQuickAction(action, title) {
    switch (action) {
        case 'verify':
            verifySource(title);
            break;
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
            openFullReport();
            break;
        default:
            alert(`Action "${action}" is not available yet.`);
    }
}

function verifySource(title) {
    const links = [];
    if (selectedResultData && selectedResultData.source_url) {
        links.push(selectedResultData.source_url);
    }
    links.push('https://www.copyright.gov/public-records/');
    links.push(`https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(title)}`);

    [...new Set(links)].forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank', 'noopener'), index * 120);
    });
}

function downloadTag(title) {
    const selected = selectedResultData || {};
    const detail = latestDetailedTagData || {};
    const tag = detail.tag || {};
    const generatedAt = new Date().toISOString();
    const fileSafeTitle = (title || 'copyright-report')
        .replace(/[\\/:*?"<>|]+/g, '')
        .trim()
        .replace(/\s+/g, '_')
        .slice(0, 80) || 'copyright-report';

    const reportUrl = buildReportUrl();
    const reportText = [
        'SCET - Copyright Validation Report',
        '=================================',
        `Generated At: ${generatedAt}`,
        '',
        `Title: ${title || 'Unknown'}`,
        `Creator: ${selected.creator || tag.creator || 'Unknown'}`,
        `Source: ${selected.source || 'Unknown'}`,
        `Source URL: ${selected.source_url || 'N/A'}`,
        `Publication Year: ${selected.publication_year || tag.publication_year || 'Unknown'}`,
        `Content Type: ${selected.content_type || 'Unknown'}`,
        `Jurisdiction: ${tag.jurisdiction || ((jurisdiction && jurisdiction.value) || 'US')}`,
        '',
        'Status Summary',
        '--------------',
        `Copyright Status: ${tag.status_text || tag.copyright_status || selected.copyright_status || 'UNKNOWN'}`,
        `Expiry Info: ${tag.expiry_info || tag.expiry_timeline || 'Not available'}`,
        `Confidence: ${Math.round((tag.confidence_score || tag.confidence || 0) * 100)}%`,
        '',
        'AI Reasoning',
        '-----------',
        tag.ai_reasoning || 'No detailed reasoning available.',
        '',
        'Shareable Report',
        '----------------',
        reportUrl,
        '',
        'Disclaimer',
        '----------',
        tag.disclaimer || 'This report is for informational purposes only and does not constitute legal advice.'
    ].join('\n');

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = downloadUrl;
    anchor.download = `SCET_Report_${fileSafeTitle}.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(downloadUrl);
}

async function shareTag(title) {
    const reportUrl = buildReportUrl();
    if (navigator.share) {
        await navigator.share({
            title: `Copyright Status: ${title}`,
            text: `Check the copyright status of "${title}" on SCET`,
            url: reportUrl
        });
    } else {
        await navigator.clipboard.writeText(reportUrl);
        alert('Report link copied to clipboard!');
    }
}

async function copyCitation(title) {
    const citation = `Copyright analysis for "${title}" generated by SCET - Smart Copyright Expiry Tag System. ${new Date().toLocaleDateString()}`;
    await navigator.clipboard.writeText(citation);
    alert('Citation copied to clipboard!');
}

function openFullReport() {
    const url = buildReportUrl();
    window.open(url, '_blank', 'noopener');
}

function buildReportPayload() {
    const selected = selectedResultData || {};
    const detail = latestDetailedTagData || {};
    const tag = detail.tag || {};

    return {
        title: selected.title || tag.title || '',
        creator: selected.creator || tag.creator || '',
        year: selected.publication_year || tag.publication_year || '',
        type: selected.content_type || detail.report_data?.content_type || '',
        jurisdiction: tag.jurisdiction || ((jurisdiction && jurisdiction.value) || 'US'),
        source: selected.source || 'Multiple Sources',
        source_url: selected.source_url || '',
        status: tag.status || selected.copyright_status || '',
        generated_at: tag.generated_at || new Date().toISOString()
    };
}

function buildReportUrl() {
    const payload = buildReportPayload();
    persistLastReport(payload);
    const params = new URLSearchParams();
    Object.entries(payload).forEach(([key, value]) => {
        if (value) {
            params.set(key, value);
        }
    });
    return `${REPORT_PAGE_PATH}?${params.toString()}`;
}

function persistLastReport(payload) {
    if (!payload || !payload.title) {
        return;
    }
    localStorage.setItem(STORAGE_KEYS.lastReport, JSON.stringify(payload));
}

function persistRecentReport(payload) {
    if (!payload || !payload.title) {
        return;
    }

    persistLastReport(payload);

    const current = loadJson(STORAGE_KEYS.recentReports, []);
    const key = `${payload.title}::${payload.creator}::${payload.year}`;
    const next = [payload, ...current.filter((item) => `${item.title}::${item.creator}::${item.year}` !== key)].slice(0, 6);
    localStorage.setItem(STORAGE_KEYS.recentReports, JSON.stringify(next));
}

function renderRecentReports() {
    if (!recentReports) {
        return;
    }

    const items = loadJson(STORAGE_KEYS.recentReports, []);
    if (!items.length) {
        recentReports.innerHTML = '<p class="premium-placeholder-text">Select a result to save a report snapshot here.</p>';
        return;
    }

    recentReports.innerHTML = items.map((item) => {
        const params = new URLSearchParams();
        Object.entries(item).forEach(([key, value]) => {
            if (value) {
                params.set(key, value);
            }
        });

        return `
            <a class="recent-report-item" href="${REPORT_PAGE_PATH}?${params.toString()}">
                <div class="recent-report-title">${escapeHtml(item.title || 'Untitled')}</div>
                <div class="recent-report-meta">
                    <span>${escapeHtml(item.type ? prettyType(item.type) : 'Unknown type')}</span>
                    <span>${escapeHtml(item.jurisdiction || 'US')}</span>
                    <span>${escapeHtml(item.year ? String(item.year) : 'Year unknown')}</span>
                </div>
            </a>
        `;
    }).join('');
}

function loadJson(key, fallback) {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
        return fallback;
    }
}

function getConfidenceColor(score) {
    if (score >= 0.8) return '#28a745';
    if (score >= 0.6) return '#ffc107';
    if (score >= 0.4) return '#fd7e14';
    return '#dc3545';
}

function showLoading() {
    if (loadingIndicator) {
        loadingIndicator.classList.remove('hidden');
    }
}

function hideLoading() {
    if (loadingIndicator) {
        loadingIndicator.classList.add('hidden');
    }
}

function hideElements(elements) {
    elements.filter(Boolean).forEach((element) => element.classList.add('hidden'));
}

function displayError(message) {
    if (resultsList && searchResults) {
        resultsList.innerHTML = `<p class="error-message" style="color: var(--danger-color); text-align: center; padding: 20px;">${escapeHtml(message)}</p>`;
        searchResults.classList.remove('hidden');
    }
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function formatStatus(status) {
    return String(status || '').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function prettyType(value) {
    return String(value || '').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getColorVar(color) {
    const colorMap = {
        green: 'success',
        yellow: 'warning',
        orange: 'warning',
        red: 'danger',
        gray: 'gray-500'
    };
    return colorMap[color] || 'gray-500';
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('SCET Frontend loaded - v4.0');

    if (searchInput) {
        searchInput.focus();
    }

    checkApiHealth();
    renderRecentReports();

    if (isSearchPage) {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('query');
        const type = urlParams.get('type');
        const country = urlParams.get('country');
        const source = urlParams.get('source');

        if (query) {
            searchInput.value = query;
            if (type && contentType) contentType.value = type;
            if (country && jurisdiction) jurisdiction.value = country;
            if (source && metadataSource) metadataSource.value = source;

            setTimeout(() => {
                performSearch();
            }, 300);
        }
    }
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

const examples = ['Harry Potter', 'Sherlock Holmes', 'The Great Gatsby'];

if (isSearchPage) {
    const searchBox = document.querySelector('.search-box');
    if (searchBox) {
        const searchHint = document.createElement('div');
        searchHint.className = 'search-hint';
        searchHint.style.cssText = 'font-size: 13px; color: var(--gray-500); margin-top: 8px;';
        searchHint.innerHTML = `Try: ${examples.map((example) => `<a href="#" style="color: var(--primary-color);" onclick="document.getElementById('searchInput').value='${example}';performSearch();return false;">${example}</a>`).join(' • ')}`;
        searchBox.appendChild(searchHint);
    }
}
