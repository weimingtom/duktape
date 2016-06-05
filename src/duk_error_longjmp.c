/*
 *  Do a longjmp call, calling the fatal error handler if no
 *  catchpoint exists.
 */

#include "duk_internal.h"

#if defined(DUK_USE_PREFER_SIZE)
DUK_LOCAL void duk__uncaught_minimal(duk_hthread *thr) {
	duk_fatal((duk_context *) thr, "uncaught error");
}
#endif

#if 0
DUK_LOCAL void duk__uncaught_readable(duk_hthread *thr) {
	const char *summary;
	char buf[64];

	summary = duk_push_string_tval_readable((duk_context *) thr, &thr->heap->lj.value1);
	DUK_SNPRINTF(buf, sizeof(buf), "uncaught: %s", summary);
	buf[sizeof(buf) - 1] = (char) 0;
	duk_fatal((duk_context *) thr, (const char *) buf);
}
#endif

#if !defined(DUK_USE_PREFER_SIZE)
DUK_LOCAL void duk__uncaught_error_aware(duk_hthread *thr) {
	duk_context *ctx;
	duk_tval *tv;
	const char *summary;
	char buf[64];

	ctx = (duk_context *) thr;

	/* Get error message in a side effect free way.  If that's not possible,
	 * fall back to summarizing the uncaught error.
	 */
	duk_push_tval(ctx, &thr->heap->lj.value1);
	if (duk_is_error(ctx, -1)) {
		tv = duk_hobject_find_existing_entry_tval_ptr(thr->heap, duk_require_hobject(ctx, -1), DUK_HTHREAD_STRING_MESSAGE(thr));
		if (tv) {
			duk_push_tval(ctx, tv);
		}
	}

	summary = duk_push_string_readable((duk_context *) thr, -1);
	DUK_SNPRINTF(buf, sizeof(buf), "uncaught: %s", summary);
	buf[sizeof(buf) - 1] = (char) 0;
	duk_fatal((duk_context *) thr, (const char *) buf);
}
#endif

DUK_INTERNAL void duk_err_longjmp(duk_hthread *thr) {
	DUK_ASSERT(thr != NULL);

	DUK_DD(DUK_DDPRINT("longjmp error: type=%d iserror=%d value1=%!T value2=%!T",
	                   (int) thr->heap->lj.type, (int) thr->heap->lj.iserror,
	                   &thr->heap->lj.value1, &thr->heap->lj.value2));

#if !defined(DUK_USE_CPP_EXCEPTIONS)
	/* If we don't have a jmpbuf_ptr, there is little we can do except
	 * cause a fatal error.  The caller's expectation is that we never
	 * return.
	 *
	 * With C++ exceptions we now just propagate an uncaught error
	 * instead of invoking the fatal error handler.  Because there's
	 * a dummy jmpbuf for C++ exceptions now, this could be changed.
	 */
	if (!thr->heap->lj.jmpbuf_ptr) {
		DUK_D(DUK_DPRINT("uncaught error: type=%d iserror=%d value1=%!T value2=%!T",
		                 (int) thr->heap->lj.type, (int) thr->heap->lj.iserror,
		                 &thr->heap->lj.value1, &thr->heap->lj.value2));

#if defined(DUK_USE_PREFER_SIZE)
		duk__uncaught_minimal(thr);
#else
		duk__uncaught_error_aware(thr);
#endif
		DUK_UNREACHABLE();
	}
#endif  /* DUK_USE_CPP_EXCEPTIONS */

#if defined(DUK_USE_CPP_EXCEPTIONS)
	{
		duk_internal_exception exc;  /* dummy */
		throw exc;
	}
#else  /* DUK_USE_CPP_EXCEPTIONS */
	DUK_LONGJMP(thr->heap->lj.jmpbuf_ptr->jb);
#endif  /* DUK_USE_CPP_EXCEPTIONS */

	DUK_UNREACHABLE();
}
