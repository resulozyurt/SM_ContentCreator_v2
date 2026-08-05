# Reference assets

Brand reference images and logos live here, one folder per brand:

```
assets/reference/
  fieldpie/   # logo.png + up to 14 reference images for brand consistency
  evatro/     # logo.png + reference images
```

These feed the image provider (Phase 4) so generated visuals stay on-brand.
Large binary assets are kept out of the app logic; paths are referenced from
each brand's YAML profile (app/brands/*.yaml).
