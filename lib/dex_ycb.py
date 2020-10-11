import os
import yaml
import numpy as np

_SUBJECTS = [
    '20200709-weiy',
    '20200813-ceppner',
    '20200820-amousavian',
    '20200903-ynarang',
    '20200908-yux',
    '20200918-ftozetoramos',
]

_SERIALS = [
    '836212060125',
    '839512060362',
    '840412060917',
    '841412060263',
    '932122060857',
    '932122060861',
    '932122061900',
    '932122062010',
]

_YCB_CLASSES = [
    '__background__',
    '002_master_chef_can',
    '003_cracker_box',
    '004_sugar_box',
    '005_tomato_soup_can',
    '006_mustard_bottle',
    '007_tuna_fish_can',
    '008_pudding_box',
    '009_gelatin_box',
    '010_potted_meat_can',
    '011_banana',
    '019_pitcher_base',
    '021_bleach_cleanser',
    '024_bowl',
    '025_mug',
    '035_power_drill',
    '036_wood_block',
    '037_scissors',
    '040_large_marker',
    '051_large_clamp',
    '052_extra_large_clamp',
    '061_foam_brick',
]

_MANO_JOINTS = [
    'wrist',
    'thumb_mcp',
    'thumb_pip',
    'thumb_dip',
    'thumb_tip',
    'index_mcp',
    'index_pip',
    'index_dip',
    'index_tip',
    'middle_mcp',
    'middle_pip',
    'middle_dip',
    'middle_tip',
    'ring_mcp',
    'ring_pip',
    'ring_dip',
    'ring_tip',
    'little_mcp',
    'little_pip',
    'little_dip',
    'little_tip'
]

_MANO_JOINT_CONNECT = [
    [0,  1], [ 1,  2], [ 2,  3], [ 3,  4],
    [0,  5], [ 5,  6], [ 6,  7], [ 7,  8],
    [0,  9], [ 9, 10], [10, 11], [11, 12],
    [0, 13], [13, 14], [14, 15], [15, 16],
    [0, 17], [17, 18], [18, 19], [19, 20],
]

_EVAL_SUBSAMPLING_FACTOR = 4


class DexYCBDataset():

  def __init__(self, setup, split):
    self._setup = setup
    self._split = split

    self._data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    self._calib_dir = os.path.join(self._data_dir, "calibration")
    self._model_dir = os.path.join(self._data_dir, "models")

    self._color_format = "color_{:06d}.jpg"
    self._depth_format = "aligned_depth_to_color_{:06d}.png"
    self._label_format = "labels_{:06d}.npz"
    self._h = 480
    self._w = 640

    self._obj_file = [
        os.path.join(self._model_dir, x, "textured_simple.obj")
        for x in _YCB_CLASSES
    ]

    # Seen subjects, camera views, grasped objects.
    if self._setup == 's0':
      if self._split == 'train':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [i for i in range(100) if i % 5 != 4]
      if self._split == 'val':
        subject_ind = [5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [i for i in range(100) if i % 5 == 4]
      if self._split == 'test':
        subject_ind = [0, 1, 2, 3, 4]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [i for i in range(100) if i % 5 == 4]

    # Unseen subjects.
    if self._setup == 's1':
      if self._split == 'train':
        subject_ind = [0, 1, 2, 3, 4]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = list(range(100))
      if self._split == 'val':
        subject_ind = [5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = list(range(100))
      if self._split == 'test':
        raise NotImplementedError

    # Unseen camera views.
    if self._setup == 's2':
      if self._split == 'train':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [0, 1, 2, 3, 4, 5]
        sequence_ind = list(range(100))
      if self._split == 'val':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [6]
        sequence_ind = list(range(100))
      if self._split == 'test':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [7]
        sequence_ind = list(range(100))

    # Unseen grasped objects.
    if self._setup == 's3':
      if self._split == 'train':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [
            i for i in range(100) if i // 5 not in (3, 7, 11, 15, 19)
        ]
      if self._split == 'val':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [i for i in range(100) if i // 5 in (3, 19)]
      if self._split == 'test':
        subject_ind = [0, 1, 2, 3, 4, 5]
        serial_ind = [0, 1, 2, 3, 4, 5, 6, 7]
        sequence_ind = [i for i in range(100) if i // 5 in (7, 11, 15)]

    self._subjects = [_SUBJECTS[i] for i in subject_ind]

    self._serials = [_SERIALS[i] for i in serial_ind]
    self._intrinsics = []
    for s in self._serials:
      intr_file = os.path.join(self._calib_dir, "intrinsics",
                               "{}_{}x{}.yml".format(s, self._w, self._h))
      with open(intr_file, 'r') as f:
        intr = yaml.load(f, Loader=yaml.FullLoader)
      intr = intr['color']
      self._intrinsics.append(intr)

    self._sequences = []
    self._mapping = []
    self._ycb_ids = []
    offset = 0
    for n in self._subjects:
      seq = sorted(os.listdir(os.path.join(self._data_dir, n)))
      seq = [os.path.join(n, s) for s in seq]
      assert len(seq) == 100
      seq = [seq[i] for i in sequence_ind]
      self._sequences += seq
      for i, q in enumerate(seq):
        meta_file = os.path.join(self._data_dir, q, "meta.yml")
        with open(meta_file, 'r') as f:
          meta = yaml.load(f, Loader=yaml.FullLoader)
        c = np.arange(len(self._serials))
        f = np.arange(meta['num_frames'])
        f, c = np.meshgrid(f, c)
        c = c.ravel()
        f = f.ravel()
        s = (offset + i) * np.ones_like(c)
        m = np.vstack((s, c, f)).T
        self._mapping.append(m)
        self._ycb_ids.append(meta['ycb_ids'])
      offset += len(seq)
    self._mapping = np.vstack(self._mapping)

  def __len__(self):
    return len(self._mapping)

  def __getitem__(self, idx):
    s, c, f = self._mapping[idx]
    d = os.path.join(self._data_dir, self._sequences[s], self._serials[c])
    sample = {
        'color_file': os.path.join(d, self._color_format.format(f)),
        'depth_file': os.path.join(d, self._depth_format.format(f)),
        'label_file': os.path.join(d, self._label_format.format(f)),
        'intrinsics': self._intrinsics[c],
        'ycb_ids': self._ycb_ids[s],
    }
    if self._split == 'test':
      sample['is_eval'] = f % _EVAL_SUBSAMPLING_FACTOR == 0
    return sample

  @property
  def h(self):
    return self._h

  @property
  def w(self):
    return self._w

  @property
  def obj_file(self):
    return self._obj_file

  @property
  def ycb_classes(self):
    return _YCB_CLASSES

  @property
  def mano_joints(self):
    return _MANO_JOINTS

  @property
  def mano_joint_connect(self):
    return _MANO_JOINT_CONNECT
