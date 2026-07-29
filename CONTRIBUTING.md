# Contributing

Keep all examples synthetic and all output non-deploying.

For a control-plane change:

1. add a policy or compilation test for the behavior;
2. preserve deterministic resource fingerprints;
3. keep compilation separate from mutation;
4. document any policy compatibility change;
5. run `make check` and `make demo`.

Do not add credentials, real infrastructure identifiers, automatic deletion, or
production-deployment claims. Provider adapters require explicit authorization,
read-only discovery tests, scoped credentials, and an approval design.

