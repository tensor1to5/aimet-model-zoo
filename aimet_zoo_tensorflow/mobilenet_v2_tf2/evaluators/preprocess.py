#pylint: skip-file
# ==============================================================================
# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import numpy as np
import tensorflow as tf
from tensorflow.python.keras.preprocessing import dataset_utils

ALLOWLIST_FORMATS = (".bmp", ".gif", ".jpeg", ".jpg", ".png", ".JPEG")

ResizeMethod = tf.image.ResizeMethod

_TF_INTERPOLATION_METHODS = {
    "bilinear": ResizeMethod.BILINEAR,
    "nearest": ResizeMethod.NEAREST_NEIGHBOR,
    "bicubic": ResizeMethod.BICUBIC,
    "area": ResizeMethod.AREA,
    "lanczos3": ResizeMethod.LANCZOS3,
    "lanczos5": ResizeMethod.LANCZOS5,
    "gaussian": ResizeMethod.GAUSSIAN,
    "mitchellcubic": ResizeMethod.MITCHELLCUBIC,
}

def paths_and_labels_to_dataset(
    image_paths,
    image_size,
    num_channels,
    labels,
    label_mode,
    num_classes,
    interpolation,
    crop_to_aspect_ratio=False,
):
    """Constructs a dataset of images and labels."""
    # TODO(fchollet): consider making num_parallel_calls settable
    path_ds = tf.data.Dataset.from_tensor_slices(image_paths)
    args = (image_size, num_channels, interpolation, crop_to_aspect_ratio)
    img_ds = path_ds.map(
        lambda x: load_image(x, *args), num_parallel_calls=tf.data.AUTOTUNE
    )
    if label_mode:
        label_ds = dataset_utils.labels_to_dataset(
            labels, label_mode, num_classes
        )
        img_ds = tf.data.Dataset.zip((img_ds, label_ds))
    return img_ds

def load_image(
    path, image_size, num_channels, interpolation, crop_to_aspect_ratio=False
):
    """Load an image from a path and resize it."""

    img = tf.io.read_file(path)

    img = tf.image.decode_image(
        img, channels=num_channels, expand_animations=False
    )

    # crop_to_aspect_ratio = False
    if crop_to_aspect_ratio:
        # img = image_utils.smart_resize(
        #     img, image_size, interpolation=interpolation
        # )
        img = smart_resize(
            img, image_size, interpolation=interpolation
        )
    else:
        img = tf.image.resize(img, image_size, method=interpolation)
    img.set_shape((image_size[0], image_size[1], num_channels))
    return img

def image_dataset_from_directory(
    directory,
    labels="inferred",
    label_mode="int",
    class_names=None,
    color_mode="rgb",
    batch_size=32,
    image_size=(256, 256),
    shuffle=True,
    seed=None,
    validation_split=None,
    subset=None,
    interpolation="bilinear",
    follow_links=False,
    crop_to_aspect_ratio=False,
    **kwargs,
):
    """Generates a `tf.data.Dataset` from image files in a directory.
    If your directory structure is:
    ```
    main_directory/
    ...class_a/
    ......a_image_1.jpg
    ......a_image_2.jpg
    ...class_b/
    ......b_image_1.jpg
    ......b_image_2.jpg
    ```
    Then calling `image_dataset_from_directory(main_directory,
    labels='inferred')` will return a `tf.data.Dataset` that yields batches of
    images from the subdirectories `class_a` and `class_b`, together with labels
    0 and 1 (0 corresponding to `class_a` and 1 corresponding to `class_b`).
    Supported image formats: jpeg, png, bmp, gif.
    Animated gifs are truncated to the first frame.
    Args:
      directory: Directory where the data is located.
          If `labels` is "inferred", it should contain
          subdirectories, each containing images for a class.
          Otherwise, the directory structure is ignored.
      labels: Either "inferred"
          (labels are generated from the directory structure),
          None (no labels),
          or a list/tuple of integer labels of the same size as the number of
          image files found in the directory. Labels should be sorted according
          to the alphanumeric order of the image file paths
          (obtained via `os.walk(directory)` in Python).
      label_mode: String describing the encoding of `labels`. Options are:
          - 'int': means that the labels are encoded as integers
              (e.g. for `sparse_categorical_crossentropy` loss).
          - 'categorical' means that the labels are
              encoded as a categorical vector
              (e.g. for `categorical_crossentropy` loss).
          - 'binary' means that the labels (there can be only 2)
              are encoded as `float32` scalars with values 0 or 1
              (e.g. for `binary_crossentropy`).
          - None (no labels).
      class_names: Only valid if "labels" is "inferred". This is the explicit
          list of class names (must match names of subdirectories). Used
          to control the order of the classes
          (otherwise alphanumerical order is used).
      color_mode: One of "grayscale", "rgb", "rgba". Default: "rgb".
          Whether the images will be converted to
          have 1, 3, or 4 channels.
      batch_size: Size of the batches of data. Default: 32.
        If `None`, the data will not be batched
        (the dataset will yield individual samples).
      image_size: Size to resize images to after they are read from disk,
          specified as `(height, width)`. Defaults to `(256, 256)`.
          Since the pipeline processes batches of images that must all have
          the same size, this must be provided.
      shuffle: Whether to shuffle the data. Default: True.
          If set to False, sorts the data in alphanumeric order.
      seed: Optional random seed for shuffling and transformations.
      validation_split: Optional float between 0 and 1,
          fraction of data to reserve for validation.
      subset: Subset of the data to return.
          One of "training", "validation" or "both".
          Only used if `validation_split` is set.
          When `subset="both"`, the utility returns a tuple of two datasets
          (the training and validation datasets respectively).
      interpolation: String, the interpolation method used when resizing images.
        Defaults to `bilinear`. Supports `bilinear`, `nearest`, `bicubic`,
        `area`, `lanczos3`, `lanczos5`, `gaussian`, `mitchellcubic`.
      follow_links: Whether to visit subdirectories pointed to by symlinks.
          Defaults to False.
      crop_to_aspect_ratio: If True, resize the images without aspect
        ratio distortion. When the original aspect ratio differs from the target
        aspect ratio, the output image will be cropped so as to return the
        largest possible window in the image (of size `image_size`) that matches
        the target aspect ratio. By default (`crop_to_aspect_ratio=False`),
        aspect ratio may not be preserved.
      **kwargs: Legacy keyword arguments.
    Returns:
      A `tf.data.Dataset` object.
        - If `label_mode` is None, it yields `float32` tensors of shape
          `(batch_size, image_size[0], image_size[1], num_channels)`,
          encoding images (see below for rules regarding `num_channels`).
        - Otherwise, it yields a tuple `(images, labels)`, where `images`
          has shape `(batch_size, image_size[0], image_size[1], num_channels)`,
          and `labels` follows the format described below.
    Rules regarding labels format:
      - if `label_mode` is `int`, the labels are an `int32` tensor of shape
        `(batch_size,)`.
      - if `label_mode` is `binary`, the labels are a `float32` tensor of
        1s and 0s of shape `(batch_size, 1)`.
      - if `label_mode` is `categorical`, the labels are a `float32` tensor
        of shape `(batch_size, num_classes)`, representing a one-hot
        encoding of the class index.
    Rules regarding number of channels in the yielded images:
      - if `color_mode` is `grayscale`,
        there's 1 channel in the image tensors.
      - if `color_mode` is `rgb`,
        there are 3 channels in the image tensors.
      - if `color_mode` is `rgba`,
        there are 4 channels in the image tensors.
    """
    if "smart_resize" in kwargs:
        crop_to_aspect_ratio = kwargs.pop("smart_resize")
    if kwargs:
        raise TypeError(f"Unknown keywords argument(s): {tuple(kwargs.keys())}")
    if labels not in ("inferred", None):
        if not isinstance(labels, (list, tuple)):
            raise ValueError(
                "`labels` argument should be a list/tuple of integer labels, "
                "of the same size as the number of image files in the target "
                "directory. If you wish to infer the labels from the "
                "subdirectory "
                'names in the target directory, pass `labels="inferred"`. '
                "If you wish to get a dataset that only contains images "
                f"(no labels), pass `labels=None`. Received: labels={labels}"
            )
        if class_names:
            raise ValueError(
                "You can only pass `class_names` if "
                f'`labels="inferred"`. Received: labels={labels}, and '
                f"class_names={class_names}"
            )
    if label_mode not in {"int", "categorical", "binary", None}:
        raise ValueError(
            '`label_mode` argument must be one of "int", '
            '"categorical", "binary", '
            f"or None. Received: label_mode={label_mode}"
        )
    if labels is None or label_mode is None:
        labels = None
        label_mode = None
    if color_mode == "rgb":
        num_channels = 3
    elif color_mode == "rgba":
        num_channels = 4
    elif color_mode == "grayscale":
        num_channels = 1
    else:
        raise ValueError(
            '`color_mode` must be one of {"rgb", "rgba", "grayscale"}. '
            f"Received: color_mode={color_mode}"
        )
    # interpolation = image_utils.get_interpolation(interpolation)
    interpolation = get_interpolation(interpolation)
    # dataset_utils.check_validation_split_arg(
    #     validation_split, subset, shuffle, seed
    # )

    if seed is None:
        seed = np.random.randint(1e6)
    image_paths, labels, class_names = dataset_utils.index_directory(
        directory,
        labels,
        formats=ALLOWLIST_FORMATS,
        class_names=class_names,
        shuffle=shuffle,
        seed=seed,
        follow_links=follow_links,
    )

    if label_mode == "binary" and len(class_names) != 2:
        raise ValueError(
            'When passing `label_mode="binary"`, there must be exactly 2 '
            f"class_names. Received: class_names={class_names}"
        )

    if subset == "both":
        (
            image_paths_train,
            labels_train,
        ) = dataset_utils.get_training_or_validation_split(
            image_paths, labels, validation_split, "training"
        )
        (
            image_paths_val,
            labels_val,
        ) = dataset_utils.get_training_or_validation_split(
            image_paths, labels, validation_split, "validation"
        )
        if not image_paths_train:
            raise ValueError(
                f"No training images found in directory {directory}. "
                f"Allowed formats: {ALLOWLIST_FORMATS}"
            )
        if not image_paths_val:
            raise ValueError(
                f"No validation images found in directory {directory}. "
                f"Allowed formats: {ALLOWLIST_FORMATS}"
            )
        train_dataset = paths_and_labels_to_dataset(
            image_paths=image_paths_train,
            image_size=image_size,
            num_channels=num_channels,
            labels=labels_train,
            label_mode=label_mode,
            num_classes=len(class_names),
            interpolation=interpolation,
            crop_to_aspect_ratio=crop_to_aspect_ratio,
        )
        val_dataset = paths_and_labels_to_dataset(
            image_paths=image_paths_val,
            image_size=image_size,
            num_channels=num_channels,
            labels=labels_val,
            label_mode=label_mode,
            num_classes=len(class_names),
            interpolation=interpolation,
            crop_to_aspect_ratio=crop_to_aspect_ratio,
        )
        train_dataset = train_dataset.prefetch(tf.data.AUTOTUNE)
        val_dataset = val_dataset.prefetch(tf.data.AUTOTUNE)
        if batch_size is not None:
            if shuffle:
                # Shuffle locally at each iteration
                train_dataset = train_dataset.shuffle(
                    buffer_size=batch_size * 8, seed=seed
                )
            train_dataset = train_dataset.batch(batch_size)
            val_dataset = val_dataset.batch(batch_size)
        else:
            if shuffle:
                train_dataset = train_dataset.shuffle(
                    buffer_size=1024, seed=seed
                )

        # Users may need to reference `class_names`.
        train_dataset.class_names = class_names
        val_dataset.class_names = class_names
        # Include file paths for images as attribute.
        train_dataset.file_paths = image_paths_train
        val_dataset.file_paths = image_paths_val
        dataset = [train_dataset, val_dataset]
    else:
        image_paths, labels = dataset_utils.get_training_or_validation_split(
            image_paths, labels, validation_split, subset
        )
        if not image_paths:
            raise ValueError(
                f"No images found in directory {directory}. "
                f"Allowed formats: {ALLOWLIST_FORMATS}"
            )

        dataset = paths_and_labels_to_dataset(
            image_paths=image_paths,
            image_size=image_size,
            num_channels=num_channels,
            labels=labels,
            label_mode=label_mode,
            num_classes=len(class_names),
            interpolation=interpolation,
            crop_to_aspect_ratio=crop_to_aspect_ratio,
        )
        dataset = dataset.prefetch(tf.data.AUTOTUNE)
        if batch_size is not None:
            if shuffle:
                # Shuffle locally at each iteration
                dataset = dataset.shuffle(buffer_size=batch_size * 8, seed=seed)
            dataset = dataset.batch(batch_size)
        else:
            if shuffle:
                dataset = dataset.shuffle(buffer_size=1024, seed=seed)

        # Users may need to reference `class_names`.
        dataset.class_names = class_names
        # Include file paths for images as attribute.
        dataset.file_paths = image_paths
    return dataset


def smart_resize(x, size, interpolation="bilinear"):
    """Resize images to a target size without aspect ratio distortion.
    Warning: `tf.keras.preprocessing.image.smart_resize` is not recommended for
    new code. Prefer `tf.keras.layers.Resizing`, which provides the same
    functionality as a preprocessing layer and adds `tf.RaggedTensor` support.
    See the [preprocessing layer guide](
    https://www.tensorflow.org/guide/keras/preprocessing_layers)
    for an overview of preprocessing layers.
    TensorFlow image datasets typically yield images that have each a different
    size. However, these images need to be batched before they can be
    processed by Keras layers. To be batched, images need to share the same
    height and width.
    You could simply do:
    ```python
    size = (200, 200)
    ds = ds.map(lambda img: tf.image.resize(img, size))
    ```
    However, if you do this, you distort the aspect ratio of your images, since
    in general they do not all have the same aspect ratio as `size`. This is
    fine in many cases, but not always (e.g. for GANs this can be a problem).
    Note that passing the argument `preserve_aspect_ratio=True` to `resize`
    will preserve the aspect ratio, but at the cost of no longer respecting the
    provided target size. Because `tf.image.resize` doesn't crop images,
    your output images will still have different sizes.
    This calls for:
    ```python
    size = (200, 200)
    ds = ds.map(lambda img: smart_resize(img, size))
    ```
    Your output images will actually be `(200, 200)`, and will not be distorted.
    Instead, the parts of the image that do not fit within the target size
    get cropped out.
    The resizing process is:
    1. Take the largest centered crop of the image that has the same aspect
    ratio as the target size. For instance, if `size=(200, 200)` and the input
    image has size `(340, 500)`, we take a crop of `(340, 340)` centered along
    the width.
    2. Resize the cropped image to the target size. In the example above,
    we resize the `(340, 340)` crop to `(200, 200)`.
    Args:
      x: Input image or batch of images (as a tensor or NumPy array). Must be in
        format `(height, width, channels)` or `(batch_size, height, width,
        channels)`.
      size: Tuple of `(height, width)` integer. Target size.
      interpolation: String, interpolation to use for resizing. Defaults to
        `'bilinear'`. Supports `bilinear`, `nearest`, `bicubic`, `area`,
        `lanczos3`, `lanczos5`, `gaussian`, `mitchellcubic`.
    Returns:
      Array with shape `(size[0], size[1], channels)`. If the input image was a
      NumPy array, the output is a NumPy array, and if it was a TF tensor,
      the output is a TF tensor.
    """
    if len(size) != 2:
        raise ValueError(
            f"Expected `size` to be a tuple of 2 integers, but got: {size}."
        )
    img = tf.convert_to_tensor(x)
    if img.shape.rank is not None:
        if img.shape.rank < 3 or img.shape.rank > 4:
            raise ValueError(
                "Expected an image array with shape `(height, width, "
                "channels)`, or `(batch_size, height, width, channels)`, but "
                f"got input with incorrect rank, of shape {img.shape}."
            )
    shape = tf.shape(img)
    height, width = shape[-3], shape[-2]
    target_height, target_width = size
    if img.shape.rank is not None:
        static_num_channels = img.shape[-1]
    else:
        static_num_channels = None

    crop_height = tf.cast(
        tf.cast(width * target_height, "float32") / target_width, "int32"
    )
    crop_width = tf.cast(
        tf.cast(height * target_width, "float32") / target_height, "int32"
    )

    # Set back to input height / width if crop_height / crop_width is not
    # smaller.
    crop_height = tf.minimum(height, crop_height)
    crop_width = tf.minimum(width, crop_width)

    crop_box_hstart = tf.cast(
        tf.cast(height - crop_height, "float32") / 2, "int32"
    )
    crop_box_wstart = tf.cast(
        tf.cast(width - crop_width, "float32") / 2, "int32"
    )

    if img.shape.rank == 4:
        crop_box_start = tf.stack([0, crop_box_hstart, crop_box_wstart, 0])
        crop_box_size = tf.stack([-1, crop_height, crop_width, -1])
    else:
        crop_box_start = tf.stack([crop_box_hstart, crop_box_wstart, 0])
        crop_box_size = tf.stack([crop_height, crop_width, -1])

    img = tf.slice(img, crop_box_start, crop_box_size)
    img = tf.image.resize(images=img, size=size, method=interpolation)
    # Apparent bug in resize_images_v2 may cause shape to be lost
    if img.shape.rank is not None:
        if img.shape.rank == 4:
            img.set_shape((None, None, None, static_num_channels))
        if img.shape.rank == 3:
            img.set_shape((None, None, static_num_channels))
    if isinstance(x, np.ndarray):
        return img.numpy()
    return img

def get_interpolation(interpolation):
    interpolation = interpolation.lower()
    if interpolation not in _TF_INTERPOLATION_METHODS:
        raise NotImplementedError(
            "Value not recognized for `interpolation`: {}. Supported values "
            "are: {}".format(interpolation, _TF_INTERPOLATION_METHODS.keys())
        )
    return _TF_INTERPOLATION_METHODS[interpolation]