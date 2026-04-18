import client from './client'

export default {
  list(sessionId) {
    return client.get(`/sessions/${sessionId}/files`)
  },

  upload(sessionId, file, fileType) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    return client.post(`/sessions/${sessionId}/files`, formData)
  },

  // 临时文件上传（不上传数据库，仅保存文件后返回路径）
  uploadTemp(sessionId, file, fileType) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    return client.post(`/sessions/${sessionId}/temp-files/upload`, formData)
  },

  // 删除临时文件
  deleteTempFile(sessionId, filePath) {
    return client.delete(`/sessions/${sessionId}/temp-files/${encodeURIComponent(filePath)}`)
  },

  updateSelection(sessionId, selections) {
    return client.patch(`/sessions/${sessionId}/files/selection`, selections)
  },

  delete(sessionId, fileId) {
    return client.delete(`/sessions/${sessionId}/files/${fileId}`)
  },
}
