// YouTube Music Copyright Checker frontend
const songInput = document.getElementById('ytSongTitle');
const artistInput = document.getElementById('ytArtistName');
const checkBtn = document.getElementById('ytCheckBtn');
const loading = document.getElementById('ytLoading');
const errorBox = document.getElementById('ytError');
const resultSection = document.getElementById('ytResultSection');
const resultCard = document.getElementById('ytResultCard');

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

const RISK_KEYWORDS = {
    high: ['vevo', 'official', 'official music video'],
    claim: ['remix', 'lyrics', 'cover'],
    safe: ['ncs', 'no copyright', 'free music']
};

checkBtn.addEventListener('click', runYoutubeCheck);
songInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runYoutubeCheck();
});
artistInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runYoutubeCheck();
});

async function runYoutubeCheck() {
    const title = songInput.value.trim();
    const artist = artistInput.value.trim();

    if (!title) {
        showError('Please enter Song Title.');
        return;
    }

    hideError();
    setLoading(true);
    resultSection.classList.add('hidden');

    try {
        const params = new URLSearchParams({ title, artist });
        const response = await fetch(`${API_BASE}/api/youtube-check?${params.toString()}`);
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Failed to check copyright');
        }

        const enhanced = buildEnhancedResult(data, title, artist);
        renderMusicResultCard(enhanced);
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        showError(err.message || 'Could not fetch metadata. Try again.');
    } finally {
        setLoading(false);
    }
}

function buildEnhancedResult(data, queryTitle, queryArtist) {
    const extractedArtist = (data.artist && data.artist !== 'Unknown')
        ? data.artist
        : extractArtistFromQuery(queryTitle, queryArtist);

    const inferredChannel = inferChannelName(data, extractedArtist);
    const localSignals = evaluateRiskSignals(queryTitle, extractedArtist, inferredChannel, data.song || queryTitle);
    const mergedRisk = mergeRisk(localSignals, data.youtube_usage_risk || 'MEDIUM', data.confidence_score || 0);

    return {
        ...data,
        extracted_artist: extractedArtist || 'Unknown',
        inferred_channel: inferredChannel,
        risk_level: mergedRisk.level,
        risk_badge_text: mergedRisk.badge,
        risk_note: mergedRisk.note,
        confidence_label: mergedRisk.confidenceLabel,
        confidence_visual: mergedRisk.confidenceVisual,
        confidence_score: mergedRisk.confidenceScore,
        thumbnail_url: buildThumbnailUrl(data.song || queryTitle, extractedArtist || queryArtist),
        suggestion: mergedRisk.level === 'HIGH'
            ? 'This song is likely copyrighted. Try using no-copyright alternatives.'
            : ''
    };
}

function evaluateRiskSignals(queryTitle, artist, channelTitle, resultTitle) {
    const normalized = [queryTitle, artist, channelTitle, resultTitle]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

    const highMatches = countKeywordMatches(normalized, RISK_KEYWORDS.high);
    const claimMatches = countKeywordMatches(normalized, RISK_KEYWORDS.claim);
    const safeMatches = countKeywordMatches(normalized, RISK_KEYWORDS.safe);

    if (safeMatches > 0) {
        return { level: 'LOW', strength: safeMatches >= 2 ? 'HIGH' : 'MEDIUM', reason: 'Safe-use keywords detected' };
    }

    if (highMatches > 0) {
        return { level: 'HIGH', strength: highMatches >= 2 ? 'HIGH' : 'MEDIUM', reason: 'Official/VEVO signal detected' };
    }

    if (claimMatches > 0) {
        return { level: 'CLAIM', strength: claimMatches >= 2 ? 'HIGH' : 'MEDIUM', reason: 'Remix/lyrics/cover signal detected' };
    }

    return { level: 'UNKNOWN', strength: 'LOW', reason: 'Weak keyword signal' };
}

function mergeRisk(signal, apiRisk, apiConfidence) {
    const normalizedApi = (apiRisk || 'MEDIUM').toUpperCase();
    let finalLevel = normalizedApi;
    let note = 'Estimated from metadata signals and API response.';

    if (signal.level === 'LOW') {
        finalLevel = 'LOW';
        note = signal.reason;
    } else if (signal.level === 'HIGH') {
        finalLevel = 'HIGH';
        note = signal.reason;
    } else if (signal.level === 'CLAIM') {
        finalLevel = 'CLAIM';
        note = signal.reason;
    }

    const confidenceVisual = signal.strength === 'HIGH' ? 88 : signal.strength === 'MEDIUM' ? 72 : 56;
    const confidenceLabel = signal.strength === 'HIGH' ? 'High' : signal.strength === 'MEDIUM' ? 'Medium' : 'Low';
    const confidenceScore = Math.max(Number(apiConfidence || 0), confidenceVisual / 100);

    const badge = finalLevel === 'HIGH'
        ? '🔴 High Risk'
        : finalLevel === 'LOW'
            ? '🟢 Safe to Use'
            : finalLevel === 'CLAIM'
                ? '🟡 Possible Content ID Claim'
                : '🟡 Medium Risk';

    return {
        level: finalLevel,
        badge,
        note,
        confidenceLabel,
        confidenceVisual,
        confidenceScore: Number(confidenceScore.toFixed(2))
    };
}

function renderMusicResultCard(data) {
    const riskClass =
        data.risk_level === 'HIGH' ? 'badge-protected' :
        data.risk_level === 'LOW' ? 'badge-public' : 'badge-unknown';

    const usesHtml = (data.allowed_uses || []).map((u) => `<li>${escapeHtml(u)}</li>`).join('');
    const sourcesHtml = (data.sources || [])
        .filter((s) => s.used)
        .map((s) => {
            if (s.url) {
                return `<li><a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name)}</a></li>`;
            }
            return `<li>${escapeHtml(s.name)}</li>`;
        })
        .join('') || '<li>Metadata API</li>';

    resultCard.innerHTML = `
        <div class="smart-tag youtube-result-card">
            <div class="youtube-media-head">
                <img class="youtube-thumb" src="${escapeHtml(data.thumbnail_url)}" alt="Song thumbnail">
                <div class="youtube-media-meta">
                    <h4 class="youtube-media-title">${escapeHtml(data.song || 'Unknown')}</h4>
                    <p class="youtube-media-channel">Channel: ${escapeHtml(data.inferred_channel || 'Unknown Channel')}</p>
                    <p class="youtube-media-artist">Extracted Artist: ${escapeHtml(data.extracted_artist || 'Unknown')}</p>
                </div>
            </div>

            <div class="music-card-grid">
                <div class="music-row"><strong>Title:</strong> ${escapeHtml(data.song || 'Unknown')}</div>
                <div class="music-row"><strong>Artist:</strong> ${escapeHtml(data.artist || 'Unknown')}</div>
                <div class="music-row"><strong>Release Year:</strong> ${escapeHtml(String(data.release_year || 'Unknown'))}</div>
                <div class="music-row"><strong>Publisher / Label:</strong> ${escapeHtml(data.publisher_label || 'Unknown')}</div>
                <div class="music-row"><strong>Copyright Status:</strong> ${escapeHtml(data.copyright_status || 'UNCLEAR')}</div>
                <div class="music-row"><strong>YouTube Usage Risk:</strong> <span class="result-badge ${riskClass}">${escapeHtml(data.risk_badge_text || '🟡 Medium Risk')}</span></div>
            </div>

            <div class="tag-section confidence-section">
                <h4>Confidence</h4>
                <div class="yt-confidence-track">
                    <div class="yt-confidence-fill" style="width: ${data.confidence_visual || 56}%"></div>
                </div>
                <p class="yt-confidence-meta">${escapeHtml(data.confidence_label || 'Low')} confidence (${escapeHtml(String(data.confidence_score || 0))})</p>
            </div>

            <div class="tag-section">
                <h4>Allowed Uses</h4>
                <ul class="music-list">${usesHtml}</ul>
            </div>

            <div class="tag-section">
                <h4>Recommendation</h4>
                <p>${escapeHtml(data.recommendation || 'Use licensed or royalty-free music.')}</p>
                ${data.suggestion ? `<div class="yt-smart-suggestion">💡 ${escapeHtml(data.suggestion)} <a href="#" data-suggest="true">No copyright music</a></div>` : ''}
            </div>

            <div class="tag-section">
                <h4>Sources</h4>
                <ul class="music-list">${sourcesHtml}</ul>
                <p class="yt-risk-note">${escapeHtml(data.risk_note || '')}</p>
            </div>

            <div class="tag-disclaimer">⚠️ This tool provides estimated copyright risk based on public data. Final results depend on YouTube Content ID system.</div>
        </div>
    `;

    const suggestLink = resultCard.querySelector('[data-suggest="true"]');
    if (suggestLink) {
        suggestLink.addEventListener('click', (event) => {
            event.preventDefault();
            songInput.value = 'No copyright music';
            artistInput.value = '';
            runYoutubeCheck();
        });
    }
}

function countKeywordMatches(text, keywords) {
    return keywords.reduce((count, keyword) => count + (text.includes(keyword.toLowerCase()) ? 1 : 0), 0);
}

function extractArtistFromQuery(title, artist) {
    if (artist) return artist;
    if (!title) return '';
    if (title.includes('-')) {
        const pieces = title.split('-');
        if (pieces.length > 1) return pieces[1].trim();
    }
    return '';
}

function inferChannelName(data, extractedArtist) {
    const songText = `${data.song || ''} ${data.artist || ''}`.toLowerCase();
    if (songText.includes('official') || songText.includes('vevo')) {
        return `${extractedArtist || 'Unknown'} Official`;
    }
    return extractedArtist ? `${extractedArtist} Channel` : 'Estimated Music Channel';
}

function buildThumbnailUrl(song, artist) {
    const text = encodeURIComponent(`${song || 'Song'} ${artist || 'Music'}`.trim());
    return `https://ui-avatars.com/api/?name=${text}&background=111827&color=93c5fd&size=256&rounded=true&bold=true`;
}

function setLoading(state) {
    loading.classList.toggle('hidden', !state);
    checkBtn.disabled = state;
    checkBtn.classList.toggle('is-loading', state);
}

function showError(msg) {
    errorBox.innerHTML = `<span>${escapeHtml(msg)}</span>`;
    errorBox.classList.remove('hidden');
}

function hideError() {
    errorBox.classList.add('hidden');
    errorBox.innerHTML = '';
}

function escapeHtml(value) {
    const str = String(value ?? '');
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
