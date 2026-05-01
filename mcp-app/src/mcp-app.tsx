import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './global.css'
import styles from './upload.module.css'
import { useMixcloudUploader } from './useMixcloudUploader.js'
import powerFmLogo from './assets/logo_yellow_64.svg'

function Header() {
  return (
    <header className={styles.header}>
      <span className={styles.headerTitle}>Mixcloud Upload</span>
      <a
        href="https://powerfm.org"
        target="_blank"
        rel="noopener noreferrer"
        className={styles.headerRight}
      >
        <span className={styles.poweredBy}>powered by</span>
        <img src={powerFmLogo} alt="PowerFM" className={styles.powerFmLogo} />
      </a>
    </header>
  )
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function MixcloudUploadApp() {
  const {
    mode, uploadState, uploadResult, errorMsg,
    mp3File, pictureFile, mp3InputRef, pictureInputRef,
    name, description, tags, unlisted, publishDate,
    disableComments, hideStats, hosts,
    busy, canSubmit, app, error,
    handleMp3Change, handlePictureChange,
    addTag, removeTag, updateTag, updateHost,
    setName, setDescription, setUnlisted, setPublishDate,
    setDisableComments, setHideStats,
    handleSubmit, handleReset,
  } = useMixcloudUploader()

  if (error) return <div className={styles.message}>Error: {error.message}</div>
  if (!app || mode === 'loading') return <div className={styles.message}>Loading…</div>

  if (uploadState === 'success' && uploadResult) {
    const mixcloudUrl = uploadResult.url
      ? `https://www.mixcloud.com${uploadResult.url}`
      : null
    return (
      <div className={styles.wrapper}>
        <Header />
        <div className={styles.container}>
          <div className={styles.successIcon}>✓</div>
          <p className={styles.successLabel}>Uploaded successfully</p>
          {mixcloudUrl && (
            <a
              href={mixcloudUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.successLink}
            >
              {mixcloudUrl}
            </a>
          )}
          <button className={styles.button} onClick={handleReset}>
            Upload another
          </button>
        </div>
      </div>
    )
  }

  const descLen = description.length

  return (
    <div className={styles.wrapper}>
      <Header />
      <div className={styles.container}>

        {/* ── Audio file ─────────────────────────────────────────────────── */}
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Audio file *</p>
          <label className={`${styles.dropZone} ${mp3File ? styles.dropZoneHasFile : ''}`}>
            <input
              ref={mp3InputRef}
              type="file"
              accept=".mp3,audio/mpeg"
              onChange={handleMp3Change}
              className={styles.hiddenInput}
              disabled={busy}
            />
            {mp3File ? (
              <div>
                <div className={styles.fileName}>{mp3File.name}</div>
                <div className={styles.fileMeta}>{formatBytes(mp3File.size)}</div>
              </div>
            ) : (
              <span className={styles.dropHint}>Click to choose an MP3 file</span>
            )}
          </label>
        </div>

        {/* ── Basic info ────────────────────────────────────────────────── */}
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Details</p>

          <label className={styles.fieldLabel}>
            <span className={styles.fieldName}>Name *</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={styles.input}
              placeholder="Your mix or show title"
              disabled={busy}
            />
          </label>

          <label className={styles.fieldLabel}>
            <span className={styles.fieldName}>Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={styles.textarea}
              placeholder="Optional description"
              disabled={busy}
              maxLength={1000}
            />
            <span className={`${styles.charCount} ${descLen > 1000 ? styles.charCountOver : ''}`}>
              {descLen}/1000
            </span>
          </label>

          <label className={styles.fieldLabel}>
            <span className={styles.fieldName}>Picture</span>
            <label className={`${styles.dropZone} ${styles.dropZoneSmall} ${pictureFile ? styles.dropZoneHasFile : ''}`}>
              <input
                ref={pictureInputRef}
                type="file"
                accept="image/*"
                onChange={handlePictureChange}
                className={styles.hiddenInput}
                disabled={busy}
              />
              {pictureFile ? (
                <span className={styles.fileName}>{pictureFile.name}</span>
              ) : (
                <span className={styles.dropHint}>Click to choose an image (max 10 MB)</span>
              )}
            </label>
          </label>
        </div>

        {/* ── Tags ─────────────────────────────────────────────────────────── */}
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Tags (up to 5)</p>
          {tags.map((tag, i) => (
            <div key={i} className={styles.tagRow}>
              <input
                type="text"
                value={tag}
                onChange={(e) => updateTag(i, e.target.value)}
                className={styles.tagInput}
                placeholder={`Tag ${i + 1} (e.g. House, Techno)`}
                disabled={busy}
              />
              {tags.length > 1 && (
                <button
                  type="button"
                  className={styles.iconButton}
                  onClick={() => removeTag(i)}
                  disabled={busy}
                  title="Remove tag"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          {tags.length < 5 && (
            <button
              type="button"
              className={styles.addTagButton}
              onClick={addTag}
              disabled={busy}
            >
              + Add tag
            </button>
          )}
        </div>

        {/* ── Options ──────────────────────────────────────────────────────── */}
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Options</p>
          <label className={styles.checkRow}>
            <input
              type="checkbox"
              checked={unlisted}
              onChange={(e) => setUnlisted(e.target.checked)}
              disabled={busy}
            />
            <span className={styles.checkLabel}>Unlisted (private — only accessible via link)</span>
          </label>
        </div>

        {/* ── PRO options ───────────────────────────────────────────────────── */}
        <div className={`${styles.section} ${styles.proSection}`}>
          <p className={styles.sectionTitle}>
            Advanced <span className={styles.proBadge}>PRO</span>
          </p>

          <label className={styles.fieldLabel}>
            <span className={styles.fieldName}>Scheduled publish date</span>
            <input
              type="datetime-local"
              value={publishDate}
              onChange={(e) => setPublishDate(e.target.value)}
              className={styles.input}
              disabled={busy}
            />
            <span className={styles.fieldHint}>Enter in UTC. Applies only to uploads not yet published.</span>
          </label>

          <label className={styles.checkRow}>
            <input
              type="checkbox"
              checked={disableComments}
              onChange={(e) => setDisableComments(e.target.checked)}
              disabled={busy}
            />
            <span className={styles.checkLabel}>Disable comments</span>
          </label>

          <label className={styles.checkRow}>
            <input
              type="checkbox"
              checked={hideStats}
              onChange={(e) => setHideStats(e.target.checked)}
              disabled={busy}
            />
            <span className={styles.checkLabel}>Hide play, favourite and repost counts</span>
          </label>

          <label className={styles.fieldLabel}>
            <span className={styles.fieldName}>Tagged hosts</span>
            <div className={styles.hostsGrid}>
              <input
                type="text"
                value={hosts[0]}
                onChange={(e) => updateHost(0, e.target.value)}
                className={styles.input}
                placeholder="Host 1 username"
                disabled={busy}
              />
              <input
                type="text"
                value={hosts[1]}
                onChange={(e) => updateHost(1, e.target.value)}
                className={styles.input}
                placeholder="Host 2 username"
                disabled={busy}
              />
            </div>
            <span className={styles.fieldHint}>Usernames must already be accepted hosts on your account.</span>
          </label>
        </div>

        {errorMsg && <p className={styles.errorMsg}>{errorMsg}</p>}

        <button
          className={styles.button}
          onClick={handleSubmit}
          disabled={busy || !canSubmit}
        >
          {busy ? 'Uploading…' : 'Upload to Mixcloud'}
        </button>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MixcloudUploadApp />
  </StrictMode>
)
