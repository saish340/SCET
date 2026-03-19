// YouTube Music Copyright Checker frontend
const songInput = document.getElementById('ytSongTitle');
const artistInput = document.getElementById('ytArtistName');
const checkBtn = document.getElementById('ytCheckBtn');
const loading = document.getElementById('ytLoading');
const errorBox = document.getElementById('ytError');
const resultSection = document.getElementById('ytResultSection');
const resultCard = document.getElementById('ytResultCard');

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';
const YT_API_KEY = (window.SCET_YOUTUBE_API_KEY || (window.SCET_CONFIG && window.SCET_CONFIG.youtubeApiKey) || '').trim();

const RISK_KEYWORDS = {
    high: ['vevo', 'official', 'official music video'],
    claim: ['remix', 'lyrics', 'cover'],
    safe: ['ncs', 'no copyright', 'free music']
};

const LICENSE_KEYWORDS = ['licensed to youtube by', 'copyright', 'all rights reserved'];
const FREE_SOURCES = ['nocopyrightsounds', 'ncs', 'pixabay music', 'free music'];
const HIGH_RISK_ARTISTS = ['ed sheeran', 'taylor swift', 'drake', 'imagine dragons', 'ariana grande'];

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
        const [data, ytMeta] = await Promise.all([
            fetchBaseAssessment(title, artist),
            fetchYouTubeMetadata(`${title} ${artist}`.trim())
        ]);

        if (!data || data.error) {
            throw new Error((data && data.error) || 'Failed to check copyright');
        }

        const enhanced = buildEnhancedResult(data, ytMeta, title, artist);
        renderMusicResultCard(enhanced);
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        showError(err.message || 'Could not fetch metadata. Try again.');
    } finally {
        setLoading(false);
    }
}

async function fetchBaseAssessment(title, artist) {
    const params = new URLSearchParams({ title, artist });
    const response = await fetch(`${API_BASE}/api/youtube-check?${params.toString()}`);
    const data = await response.json();
    if (!response.ok || data.error) {
        throw new Error(data.error || 'Failed to check copyright');
    }
    return data;
}

async function fetchYouTubeMetadata(searchQuery) {
    if (!YT_API_KEY) {
        return { available: false, reason: 'YouTube API key not configured' };
    }

    try {
        const searchUrl = new URL('https://www.googleapis.com/youtube/v3/search');
        searchUrl.searchParams.set('part', 'snippet');
        searchUrl.searchParams.set('type', 'video');
        searchUrl.searchParams.set('maxResults', '1');
        searchUrl.searchParams.set('q', searchQuery);
        searchUrl.searchParams.set('key', YT_API_KEY);

        const searchResp = await fetch(searchUrl.toString());
        if (!searchResp.ok) {
            throw new Error('YouTube search failed');
        }
        const searchData = await searchResp.json();
        const firstItem = searchData.items && searchData.items[0];
        if (!firstItem || !firstItem.id || !firstItem.id.videoId) {
            return { available: false, reason: 'No YouTube video match' };
        }

        const videoId = firstItem.id.videoId;
        const videoUrl = new URL('https://www.googleapis.com/youtube/v3/videos');
        videoUrl.searchParams.set('part', 'snippet,statistics');
        videoUrl.searchParams.set('id', videoId);
        videoUrl.searchParams.set('key', YT_API_KEY);

        const videoResp = await fetch(videoUrl.toString());
        if (!videoResp.ok) {
            throw new Error('YouTube video metadata fetch failed');
        }
        const videoData = await videoResp.json();
        const item = videoData.items && videoData.items[0];
        if (!item) {
            return { available: false, reason: 'No YouTube video detail' };
        }

        const snippet = item.snippet || {};
        const statistics = item.statistics || {};
        return {
            available: true,
            videoId,
            title: snippet.title || '',
            channelTitle: snippet.channelTitle || '',
            description: snippet.description || '',
            viewCount: Number(statistics.viewCount || 0),
            thumbnail: (snippet.thumbnails && (snippet.thumbnails.high || snippet.thumbnails.medium || snippet.thumbnails.default || {}).url) || ''
        };
    } catch (error) {
        return { available: false, reason: error.message || 'YouTube metadata unavailable' };
    }
}

function buildEnhancedResult(data, ytMeta, queryTitle, queryArtist) {
    const extractedArtist = (data.artist && data.artist !== 'Unknown')
        ? data.artist
        : extractArtistFromQuery(queryTitle, queryArtist);

    const inferredChannel = ytMeta.available ? ytMeta.channelTitle : inferChannelName(data, extractedArtist);
    const riskEstimation = estimateRisk({
        inputTitle: queryTitle,
        inputArtist: queryArtist,
        resultTitle: data.song || queryTitle,
        extractedArtist,
        channelTitle: inferredChannel,
        description: ytMeta.description || '',
        viewCount: ytMeta.viewCount || 0
    });

    const mergedRisk = mergeRisk(riskEstimation, data.youtube_usage_risk || 'MEDIUM', data.confidence_score || 0);

    return {
        ...data,
        extracted_artist: extractedArtist || 'Unknown',
        inferred_channel: inferredChannel,
        youtube_meta_available: !!ytMeta.available,
        youtube_meta_note: ytMeta.available ? 'YouTube Data API v3 metadata analyzed in real-time.' : (ytMeta.reason || 'YouTube metadata unavailable'),
        youtube_view_count: ytMeta.viewCount || 0,
        risk_level: mergedRisk.level,
        risk_badge_text: mergedRisk.badge,
        risk_note: mergedRisk.note,
        risk_score: mergedRisk.score,
        reason_breakdown: mergedRisk.reasons,
        confidence_label: mergedRisk.confidenceLabel,
        confidence_visual: mergedRisk.confidenceVisual,
        confidence_score: mergedRisk.confidenceScore,
        thumbnail_url: ytMeta.thumbnail || buildThumbnailUrl(data.song || queryTitle, extractedArtist || queryArtist),
        suggestion: mergedRisk.level === 'HIGH'
            ? 'This song is likely copyrighted. Try using no-copyright alternatives.'
            : ''
    };
}

function estimateRisk(ctx) {
    let score = 35;
    const reasons = [];

    const channel = (ctx.channelTitle || '').toLowerCase();
    const title = (ctx.resultTitle || ctx.inputTitle || '').toLowerCase();
    const description = (ctx.description || '').toLowerCase();
    const artist = (ctx.extractedArtist || ctx.inputArtist || '').toLowerCase();

    const isOfficialChannel = containsAny(channel, RISK_KEYWORDS.high)
        || (artist && channel.includes(artist));
    if (isOfficialChannel || title.includes('official music video')) {
        score += 50;
        reasons.push('Official channel or official music video signal detected');
    }

    if (containsAny(description, LICENSE_KEYWORDS)) {
        score += 30;
        reasons.push('Licensed/copyright text found in description');
    }

    if ((ctx.viewCount || 0) > 1000000) {
        score += 10;
        reasons.push('High popularity (>1M views) increases claim likelihood');
    }

    if (containsAny(title, RISK_KEYWORDS.claim)) {
        score += 15;
        reasons.push('Remix/lyrics/cover keyword detected');
    }

    const freeSourceHit = containsAny(channel, FREE_SOURCES)
        || containsAny(title, RISK_KEYWORDS.safe)
        || containsAny(title, ['no copyright']);
    if (freeSourceHit) {
        score -= 60;
        reasons.push('Free music source/no-copyright marker detected');
    }

    if (matchesHighRiskArtist(title, artist)) {
        score += 35;
        reasons.push('High-risk mainstream artist detected');
    }

    score = Math.max(0, Math.min(100, score));
    const level = score > 70 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW';

    return {
        score,
        level,
        reasons: reasons.length ? reasons : ['Limited public signals detected']
    };
}

function mergeRisk(signal, apiRisk, apiConfidence) {
    const normalizedApi = (apiRisk || 'MEDIUM').toUpperCase();
    const apiScore = normalizedApi === 'HIGH' ? 80 : normalizedApi === 'LOW' ? 25 : 55;
    const combinedScore = Math.round((signal.score * 0.7) + (apiScore * 0.3));

    let finalLevel = combinedScore > 70 ? 'HIGH' : combinedScore >= 40 ? 'MEDIUM' : 'LOW';
    if (normalizedApi === 'LOW' && combinedScore < 60) {
        finalLevel = 'LOW';
    }

    const note = 'Estimated from metadata signals and API response.';
    const confidenceVisual = combinedScore > 70 ? 90 : combinedScore >= 40 ? 72 : 58;
    const confidenceLabel = combinedScore > 70 ? 'High' : combinedScore >= 40 ? 'Medium' : 'Low';
    const confidenceScore = Math.max(Number(apiConfidence || 0), confidenceVisual / 100);

    const badge = finalLevel === 'HIGH'
        ? '🔴 High Risk'
        : finalLevel === 'LOW'
            ? '🟢 Safe to Use'
            : '🟡 Possible Content ID Claim';

    return {
        level: finalLevel,
        badge,
        note,
        score: combinedScore,
        reasons: signal.reasons,
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
                <h4>Risk Meter</h4>
                <div class="yt-risk-meter-track">
                    <div class="yt-risk-meter-fill ${riskClass}" style="width: ${data.risk_score || 0}%"></div>
                </div>
                <p class="yt-risk-score">[${buildMeterBlocks(data.risk_score || 0)}] ${data.risk_score || 0}%</p>
                <h4 class="yt-confidence-title">Confidence</h4>
                <div class="yt-confidence-track">
                    <div class="yt-confidence-fill" style="width: ${data.confidence_visual || 56}%"></div>
                </div>
                <p class="yt-confidence-meta">${escapeHtml(data.confidence_label || 'Low')} confidence (${escapeHtml(String(data.confidence_score || 0))})</p>
            </div>

            <div class="tag-section">
                <h4>Why this result</h4>
                <ul class="yt-reason-list">
                    ${(data.reason_breakdown || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}
                </ul>
                <p class="yt-meta-note">${escapeHtml(data.youtube_meta_note || '')}</p>
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

function containsAny(text, keywords) {
    const normalized = (text || '').toLowerCase();
    return keywords.some((keyword) => normalized.includes(keyword.toLowerCase()));
}

function matchesHighRiskArtist(title, artist) {
    const blob = `${title || ''} ${artist || ''}`.toLowerCase();
    return HIGH_RISK_ARTISTS.some((name) => blob.includes(name.toLowerCase()));
}

function buildMeterBlocks(score) {
    const filled = Math.max(0, Math.min(10, Math.round(score / 10)));
    return '█'.repeat(filled) + '░'.repeat(10 - filled);
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
