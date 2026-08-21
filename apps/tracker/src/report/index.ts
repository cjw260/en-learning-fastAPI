export const report = async (url: string, body: any) => {
    const blob = new Blob([JSON.stringify(body)], { type: 'application/json' })
    navigator.sendBeacon(url, blob)
}

export const reportFetch = async (url: string, body: any, accessToken?: string) => {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(body),
        keepalive: true,
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result?.message || `Tracker request failed (${response.status})`)
    return result
}
