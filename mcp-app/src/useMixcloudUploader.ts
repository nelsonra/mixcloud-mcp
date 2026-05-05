import { useApp } from '@modelcontextprotocol/ext-apps/react'
import { useCallback, useRef, useState } from 'react'

export type Mode = 'loading' | 'ready'
export type UploadState = 'idle' | 'uploading' | 'success' | 'error'

interface ToolResultData {
  status?: string
  upload_url?: string
  upload_token?: string
  error?: string
  message?: string
  auth_url?: string
}

export interface UploadResult {
  result?: {
    success: boolean
    message: string
    key: string
  }
  error?: string
}

const MAX_MP3_BYTES = 1073741824 // 1 GB — typical upper bound for a long show
const MAX_PICTURE_BYTES = 10485760

export function useMixcloudUploader() {
  const [mode, setMode] = useState<Mode>('loading')
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  const [uploadUrl, setUploadUrl] = useState<string | null>(null)
  const [uploadToken, setUploadToken] = useState<string | null>(null)

  const [mp3File, setMp3File] = useState<File | null>(null)
  const [pictureFile, setPictureFile] = useState<File | null>(null)
  const mp3InputRef = useRef<HTMLInputElement>(null)
  const pictureInputRef = useRef<HTMLInputElement>(null)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState<string[]>([''])
  const [unlisted, setUnlisted] = useState(false)
  const [publishDate, setPublishDate] = useState('')
  const [disableComments, setDisableComments] = useState(false)
  const [hideStats, setHideStats] = useState(false)
  const [hosts, setHosts] = useState<[string, string]>(['', ''])

  const { app, error } = useApp({
    appInfo: { name: 'Mixcloud Upload', version: '1.0.0' },
    capabilities: {},
    onAppCreated: (app) => {
      app.ontoolinput = async (input) => {
        const args = input.arguments as { name?: string } | undefined
        if (args?.name) setName(args.name)
      }

      app.ontoolresult = async (result) => {
        const text = result.content?.find((c) => c.type === 'text')?.text
        if (!text) return
        try {
          const data = JSON.parse(text) as ToolResultData
          if (data.error) {
            setErrorMsg(data.message ?? data.error)
            setMode('ready')
            return
          }
          if (data.upload_url) {
            setUploadUrl(data.upload_url)
            setUploadToken(data.upload_token ?? null)
            setMode('ready')
          }
        } catch {
          // Non-JSON result — stay in loading state
        }
      }

      app.onteardown = async () => ({})
      app.onerror = console.error
    },
  })

  // ── File handlers ───────────────────────────────────────────────────────────

  const handleMp3Change = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const picked = e.target.files?.[0] ?? null
      if (picked && picked.size > MAX_MP3_BYTES) {
        setErrorMsg('MP3 file exceeds the 1 GB limit.')
        e.target.value = ''
        return
      }
      setErrorMsg('')
      setMp3File(picked)
      if (picked && !name) {
        setName(picked.name.replace(/\.[^.]+$/, ''))
      }
    },
    [name]
  )

  const handlePictureChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0] ?? null
    if (picked && picked.size > MAX_PICTURE_BYTES) {
      setErrorMsg('Picture file exceeds the 10 MB limit.')
      e.target.value = ''
      return
    }
    setErrorMsg('')
    setPictureFile(picked)
  }, [])

  // ── Tag handlers ────────────────────────────────────────────────────────────

  const addTag = useCallback(() => {
    setTags((prev) => (prev.length < 5 ? [...prev, ''] : prev))
  }, [])

  const removeTag = useCallback((i: number) => {
    setTags((prev) => prev.filter((_, idx) => idx !== i))
  }, [])

  const updateTag = useCallback((i: number, value: string) => {
    setTags((prev) => prev.map((t, idx) => (idx === i ? value : t)))
  }, [])

  // ── Host handler ────────────────────────────────────────────────────────────

  const updateHost = useCallback((i: 0 | 1, value: string) => {
    setHosts((prev) => {
      const next = [...prev] as [string, string]
      next[i] = value
      return next
    })
  }, [])

  // ── Submit ──────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (!mp3File || !name.trim() || !uploadUrl) return
    setUploadState('uploading')
    setErrorMsg('')

    try {
      const formData = new FormData()
      formData.append('mp3', mp3File, mp3File.name)
      formData.append('name', name.trim())

      if (pictureFile) formData.append('picture', pictureFile, pictureFile.name)
      if (description.trim()) formData.append('description', description.trim())

      tags.forEach((tag, i) => {
        if (tag.trim()) formData.append(`tags-${i}-tag`, tag.trim())
      })

      if (unlisted) formData.append('unlisted', '1')

      if (publishDate) {
        // datetime-local gives YYYY-MM-DDTHH:MM — append seconds and Z for UTC
        const iso = publishDate.length === 16 ? `${publishDate}:00Z` : publishDate
        formData.append('publish_date', iso)
      }

      if (disableComments) formData.append('disable_comments', '1')
      if (hideStats) formData.append('hide_stats', '1')

      hosts.forEach((username, i) => {
        if (username.trim()) formData.append(`hosts-${i}-username`, username.trim())
      })

      const headers: HeadersInit = {}
      if (uploadToken) headers['Authorization'] = `Bearer ${uploadToken}`

      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers,
        body: formData,
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: response.statusText }))
        setErrorMsg((err as { error?: string }).error ?? `Upload failed (${response.status})`)
        setUploadState('error')
        return
      }

      const data = (await response.json()) as UploadResult
      const mixcloudKey = data.result?.key
      if (!mixcloudKey) {
        setErrorMsg((data as { error?: string }).error ?? 'Upload appeared to succeed but no track key was returned')
        setUploadState('error')
        return
      }

      setUploadResult(data)
      setUploadState('success')

      const mixcloudUrl = `https://www.mixcloud.com${mixcloudKey}`
      // updateModelContext is only available in a real MCP host (e.g. Claude Desktop).
      // fastmcp dev apps preview doesn't implement it — ignore the -32601 error.
      await app?.updateModelContext({
        content: [{ type: 'text', text: `Uploaded "${name.trim()}" to Mixcloud: ${mixcloudUrl}` }],
      }).catch((err) => console.error('[updateModelContext]', err))
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      const detail = message === 'Failed to fetch' && uploadUrl?.startsWith('http:')
        ? `Cannot reach upload server (${uploadUrl}). If you're connecting via Claude.ai, MCP_PUBLIC_URL must be an HTTPS URL (e.g. your ngrok address).`
        : message
      setErrorMsg(detail)
      setUploadState('error')
    }
  }, [
    mp3File, name, pictureFile, description, tags, unlisted,
    publishDate, disableComments, hideStats, hosts, uploadUrl, uploadToken, app,
  ])

  // ── Reset ───────────────────────────────────────────────────────────────────

  const handleReset = useCallback(() => {
    setMp3File(null)
    setPictureFile(null)
    setUploadState('idle')
    setErrorMsg('')
    setUploadResult(null)
    setName('')
    setDescription('')
    setTags([''])
    setUnlisted(false)
    setPublishDate('')
    setDisableComments(false)
    setHideStats(false)
    setHosts(['', ''])
    if (mp3InputRef.current) mp3InputRef.current.value = ''
    if (pictureInputRef.current) pictureInputRef.current.value = ''
  }, [])

  // ── Public API ──────────────────────────────────────────────────────────────

  return {
    mode,
    uploadState,
    uploadResult,
    errorMsg,
    mp3File,
    pictureFile,
    mp3InputRef,
    pictureInputRef,
    name,
    description,
    tags,
    unlisted,
    publishDate,
    disableComments,
    hideStats,
    hosts,
    busy: uploadState === 'uploading',
    canSubmit: !!mp3File && !!name.trim() && !!uploadUrl,
    app,
    error,
    handleMp3Change,
    handlePictureChange,
    addTag,
    removeTag,
    updateTag,
    updateHost,
    setName,
    setDescription,
    setUnlisted,
    setPublishDate,
    setDisableComments,
    setHideStats,
    handleSubmit,
    handleReset,
  }
}
