import { z } from 'zod'

export const limits = { title: 160, post: 10000, reply: 4000 }
const timestamp = z.string().datetime({ offset: true })
const authorSchema = z.object({ name: z.string(), picture: z.string().nullable() })
export const categoriesSchema = z.array(z.object({ slug: z.string(), label: z.string() }))
export const postSchema = z.object({
  id: z.string().uuid(), category: z.string(), title: z.string(), body: z.string(),
  created_at: timestamp, edited_at: timestamp.nullable(), author: authorSchema, is_mine: z.boolean(),
})
const replyFields = {
  id: z.string().uuid(), post_id: z.string().uuid(), parent_reply_id: z.string().uuid().nullable(),
  created_at: timestamp, edited_at: timestamp.nullable(), is_mine: z.boolean(),
}
export const replySchema = z.union([
  z.object({ ...replyFields, body: z.string(), author: authorSchema, deleted_at: z.null() }),
  z.object({ ...replyFields, body: z.null(), author: z.null(), deleted_at: timestamp }),
])
export const postPageSchema = z.object({ items: z.array(postSchema), next_cursor: z.string().nullable() })
export const replyPageSchema = z.object({ items: z.array(replySchema), next_cursor: z.string().nullable() })
export type Post = z.infer<typeof postSchema>
export type Reply = z.infer<typeof replySchema>
export type Category = z.infer<typeof categoriesSchema>[number]
export type Author = z.infer<typeof authorSchema>
export type PostInput = Pick<Post, 'title' | 'body' | 'category'>
export type Page<T> = { items: T[]; next_cursor: string | null }
