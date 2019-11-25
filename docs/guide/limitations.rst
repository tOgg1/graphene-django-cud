==============================
Known limitations and quirks
==============================

One could wish for an API where you could specify both IDs and objects
in a single array for many to many and many to one relations. However,
due to GraphQLs strict type system, this is not currently possible — in
particular due to the fact that scalars and object types cannot
simultaneously be part of a union.

Some workarounds could be implemented for this, but we deem this more
dirty than useful.
