/*
 *  Heap Array object representation.  Used for actual Array instances.
 *
 *  All objects with the exotic array behavior (which must coincide with having
 *  internal class array) MUST be duk_harrays.  No other object can be a
 *  duk_harray.
 */

#ifndef DUK_HARRAY_H_INCLUDED
#define DUK_HARRAY_H_INCLUDED

/* FIXME: need flag for DUK_HARRAY_FLAG_LENGTH_WRITABLE */

#define DUK_ASSERT_HARRAY_VALID(h) do { \
		DUK_ASSERT((h) != NULL); \
		DUK_ASSERT(DUK_HOBJECT_IS_ARRAY((duk_hobject *) (h))); \
		DUK_ASSERT(DUK_HOBJECT_HAS_EXOTIC_ARRAY((duk_hobject *) (h))); \
	} while (0)

struct duk_harray {
	/* Shared object part. */
	duk_hobject obj;

	/* Array length. */
	duk_uint32_t length;
	duk_bool_t length_nonwritable;
};

#endif  /* DUK_HARRAY_H_INCLUDED */
