import { FormEvent, useState } from 'react'
import { api } from '../api'
import type { Person } from '../types'

export function SourceUploader({ people, onSaved, onClose }: { people: Person[]; onSaved: () => Promise<void>; onClose: () => void }) {
  const [error, setError] = useState('')
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    try {
      const form = new FormData(event.currentTarget)
      const personId = String(form.get('linked_person_id') ?? '')
      form.delete('linked_person_id')
      const source = await api.uploadSource(form)
      if (personId) await api.linkSourceToPerson(source.id, personId)
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '上传失败')
    }
  }
  return <div className="dialog-backdrop" role="presentation"><section className="editor-card" role="dialog" aria-modal="true" aria-labelledby="source-editor-title">
    <div className="panel-title"><div><span>私密档案</span><h2 id="source-editor-title">上传资料</h2></div><button type="button" onClick={onClose}>关闭</button></div>
    <form className="editor-form" onSubmit={submit}>
      <label>资料名称<input name="title" required /></label>
      <label>资料类型<select name="source_type" defaultValue="document"><option value="document">文献 / PDF</option><option value="image">图片</option><option value="text">文字记录</option></select></label>
      <label>年代<input name="era" placeholder="如 民国三十六年" /></label>
      <label>来源<input name="provenance" placeholder="如 家中旧藏" /></label>
      <label>核实状态<select name="verification_status" defaultValue="unverified"><option value="unverified">待核实</option><option value="verified">已核实</option><option value="conflicting">存在冲突</option></select></label>
      <label>关联人物（可选）<select name="linked_person_id" defaultValue=""><option value="">暂不关联</option>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      <label>选择文件<input name="file" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.md" required /></label>
      <label className="wide-field">备注<textarea name="notes" /></label>
      {error && <p className="form-error wide-field" role="alert">{error}</p>}
      <div className="editor-actions wide-field"><button type="button" className="cancel-button" onClick={onClose}>取消</button><button className="confirm-button">安全上传</button></div>
    </form>
  </section></div>
}
