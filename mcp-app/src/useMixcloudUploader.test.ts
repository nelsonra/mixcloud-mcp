import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMixcloudUploader } from './useMixcloudUploader.js'

// --- Mock @modelcontextprotocol/ext-apps/react ---------------------------------
// The real useApp establishes a postMessage channel to the MCP host, which
// doesn't exist in jsdom. We replace it with a synchronous stub that calls
// onAppCreated immediately so we can trigger ontoolresult / ontoolinput in tests.

const mockApp = {
  updateModelContext: vi.fn().mockResolvedValue(undefined),
  ontoolinput: undefined as any,
  ontoolresult: undefined as any,
  onteardown: undefined as any,
  onerror: undefined as any,
}

vi.mock('@modelcontextprotocol/ext-apps/react', () => ({
  useApp: ({ onAppCreated }: any) => {
    onAppCreated?.(mockApp)
    return { app: mockApp, error: null }
  },
}))

// --- Helpers -------------------------------------------------------------------

const TOOL_RESULT = (uploadUrl: string, uploadToken: string | null = 'test-token') => ({
  content: [
    {
      type: 'text',
      text: JSON.stringify({ upload_url: uploadUrl, upload_token: uploadToken }),
    },
  ],
})

const UPLOAD_URL = 'http://localhost:4321/upload'

async function setupReadyHook() {
  const hook = renderHook(() => useMixcloudUploader())
  await act(async () => {
    await mockApp.ontoolresult(TOOL_RESULT(UPLOAD_URL))
  })
  return hook
}

function makeMp3File(sizeBytes = 1024) {
  return new File([new Uint8Array(sizeBytes)], 'show.mp3', { type: 'audio/mpeg' })
}

function mockFetchSuccess(key = '/powerfm/test-upload/') {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ result: { success: true, message: 'Uploaded', key } }),
  })
}

function mockFetchNoKey() {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ error: 'Upload appeared to succeed but no track key was returned' }),
  })
}

function mockFetchHttpError(status = 502, error = 'Bad Gateway') {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    statusText: error,
    json: async () => ({ error }),
  })
}

// --- Tests ---------------------------------------------------------------------

describe('useMixcloudUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApp.updateModelContext = vi.fn().mockResolvedValue(undefined)
  })

  // ── Initial state ────────────────────────────────────────────────────────────

  it('starts in loading mode', () => {
    const { result } = renderHook(() => useMixcloudUploader())
    expect(result.current.mode).toBe('loading')
    expect(result.current.uploadState).toBe('idle')
  })

  it('canSubmit is false while loading', () => {
    const { result } = renderHook(() => useMixcloudUploader())
    expect(result.current.canSubmit).toBe(false)
  })

  // ── ontoolresult ─────────────────────────────────────────────────────────────

  it('becomes ready after receiving upload_url from ontoolresult', async () => {
    const { result } = await setupReadyHook()
    expect(result.current.mode).toBe('ready')
  })

  it('stores upload token from ontoolresult', async () => {
    const hook = renderHook(() => useMixcloudUploader())
    await act(async () => {
      await mockApp.ontoolresult(TOOL_RESULT(UPLOAD_URL, 'my-token'))
    })
    // Token is internal state — verify it reaches fetch as Authorization header
    mockFetchSuccess()
    const mp3 = makeMp3File()
    await act(async () => {
      hook.result.current.handleMp3Change({ target: { files: [mp3], value: '' } } as any)
    })
    await act(async () => {
      hook.result.current.setName('Test Mix')
    })
    await act(async () => {
      await hook.result.current.handleSubmit()
    })
    const headers = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers
    expect(headers['Authorization']).toBe('Bearer my-token')
  })

  it('stays loading if ontoolresult contains no upload_url', async () => {
    const { result } = renderHook(() => useMixcloudUploader())
    await act(async () => {
      await mockApp.ontoolresult({ content: [{ type: 'text', text: '{"name":"ignored"}' }] })
    })
    expect(result.current.mode).toBe('loading')
  })

  // ── ontoolinput ──────────────────────────────────────────────────────────────

  it('prefills name from ontoolinput arguments', async () => {
    const { result } = renderHook(() => useMixcloudUploader())
    await act(async () => {
      await mockApp.ontoolinput({ arguments: { name: 'Friday Night Mix' } })
    })
    expect(result.current.name).toBe('Friday Night Mix')
  })

  // ── File validation ──────────────────────────────────────────────────────────

  it('rejects MP3 files over 4 GB', async () => {
    const { result } = await setupReadyHook()
    const oversized = new File([new Uint8Array(1)], 'big.mp3', { type: 'audio/mpeg' })
    Object.defineProperty(oversized, 'size', { value: 1073741825 })
    await act(async () => {
      result.current.handleMp3Change({ target: { files: [oversized], value: '' } } as any)
    })
    expect(result.current.errorMsg).toMatch(/1 GB/)
    expect(result.current.mp3File).toBeNull()
  })

  it('rejects picture files over 10 MB', async () => {
    const { result } = await setupReadyHook()
    const oversized = new File([new Uint8Array(1)], 'cover.jpg', { type: 'image/jpeg' })
    Object.defineProperty(oversized, 'size', { value: 10485761 })
    await act(async () => {
      result.current.handlePictureChange({ target: { files: [oversized], value: '' } } as any)
    })
    expect(result.current.errorMsg).toMatch(/10 MB/)
  })

  it('prefills name from MP3 filename when name is empty', async () => {
    const { result } = await setupReadyHook()
    const mp3 = new File([new Uint8Array(1024)], 'friday-night-set.mp3', { type: 'audio/mpeg' })
    await act(async () => {
      result.current.handleMp3Change({ target: { files: [mp3], value: '' } } as any)
    })
    expect(result.current.name).toBe('friday-night-set')
  })

  // ── canSubmit ────────────────────────────────────────────────────────────────

  it('canSubmit requires mp3, name, and upload URL', async () => {
    const { result } = await setupReadyHook()
    expect(result.current.canSubmit).toBe(false) // no file yet

    const mp3 = makeMp3File()
    await act(async () => { result.current.handleMp3Change({ target: { files: [mp3], value: '' } } as any) })
    // handleMp3Change auto-fills name from filename, so canSubmit is now true
    expect(result.current.canSubmit).toBe(true)
  })

  it('canSubmit is false when name is cleared', async () => {
    const { result } = await setupReadyHook()
    const mp3 = makeMp3File()
    await act(async () => { result.current.handleMp3Change({ target: { files: [mp3], value: '' } } as any) })
    await act(async () => { result.current.setName('') })
    expect(result.current.canSubmit).toBe(false)
  })

  // ── Successful upload ────────────────────────────────────────────────────────

  it('sets success state after upload returns a key', async () => {
    mockFetchSuccess('/powerfm/friday-night/')
    const { result } = await setupReadyHook()
    const mp3 = makeMp3File()
    await act(async () => { result.current.handleMp3Change({ target: { files: [mp3], value: '' } } as any) })
    await act(async () => { await result.current.handleSubmit() })

    expect(result.current.uploadState).toBe('success')
    expect(result.current.uploadResult?.result?.key).toBe('/powerfm/friday-night/')
  })

  it('calls updateModelContext with the Mixcloud URL on success', async () => {
    mockFetchSuccess('/powerfm/friday-night/')
    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })
    await act(async () => { result.current.setName('Friday Night') })
    await act(async () => { await result.current.handleSubmit() })

    expect(mockApp.updateModelContext).toHaveBeenCalledWith({
      content: [{ type: 'text', text: 'Uploaded "Friday Night" to Mixcloud: https://www.mixcloud.com/powerfm/friday-night/' }],
    })
  })

  it('shows busy state while uploading', async () => {
    let resolveFetch!: (v: any) => void
    globalThis.fetch = vi.fn().mockReturnValue(new Promise((r) => { resolveFetch = r }))

    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })

    act(() => { result.current.handleSubmit() })
    expect(result.current.busy).toBe(true)

    await act(async () => {
      resolveFetch({ ok: true, json: async () => ({ result: { success: true, key: '/powerfm/test/' } }) })
    })
    expect(result.current.busy).toBe(false)
  })

  // ── Failed upload ────────────────────────────────────────────────────────────

  it('sets error state when response has no key', async () => {
    mockFetchNoKey()
    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })
    await act(async () => { await result.current.handleSubmit() })

    expect(result.current.uploadState).toBe('error')
    expect(result.current.errorMsg).toBeTruthy()
  })

  it('sets error state on HTTP error response', async () => {
    mockFetchHttpError(502, 'Mixcloud rejected the file')
    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })
    await act(async () => { await result.current.handleSubmit() })

    expect(result.current.uploadState).toBe('error')
    expect(result.current.errorMsg).toBeTruthy()
  })

  it('does not call updateModelContext on failure', async () => {
    mockFetchNoKey()
    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })
    await act(async () => { await result.current.handleSubmit() })

    expect(mockApp.updateModelContext).not.toHaveBeenCalled()
  })

  // ── Reset ────────────────────────────────────────────────────────────────────

  it('resets all state back to idle after handleReset', async () => {
    mockFetchSuccess()
    const { result } = await setupReadyHook()
    await act(async () => { result.current.handleMp3Change({ target: { files: [makeMp3File()], value: '' } } as any) })
    await act(async () => { await result.current.handleSubmit() })
    expect(result.current.uploadState).toBe('success')

    await act(async () => { result.current.handleReset() })

    expect(result.current.uploadState).toBe('idle')
    expect(result.current.mp3File).toBeNull()
    expect(result.current.name).toBe('')
    expect(result.current.uploadResult).toBeNull()
    expect(result.current.errorMsg).toBe('')
  })

  // ── Tag / host handlers ──────────────────────────────────────────────────────

  it('addTag appends an empty tag up to the 5-tag limit', async () => {
    const { result } = await setupReadyHook()
    expect(result.current.tags).toHaveLength(1)
    await act(async () => { result.current.addTag() })
    expect(result.current.tags).toHaveLength(2)
  })

  it('addTag does not exceed 5 tags', async () => {
    const { result } = await setupReadyHook()
    for (let i = 0; i < 6; i++) {
      await act(async () => { result.current.addTag() })
    }
    expect(result.current.tags).toHaveLength(5)
  })

  it('removeTag removes the tag at the given index', async () => {
    const { result } = await setupReadyHook()
    await act(async () => { result.current.addTag() })
    await act(async () => { result.current.updateTag(0, 'House') })
    await act(async () => { result.current.updateTag(1, 'Techno') })
    await act(async () => { result.current.removeTag(0) })
    expect(result.current.tags).toHaveLength(1)
    expect(result.current.tags[0]).toBe('Techno')
  })
})
