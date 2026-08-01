from abc import ABC, abstractmethod
import torch
import numpy as np
import cv2
from PIL import Image as PilImage
from deoldify import device as device_settings
import logging
from torchvision import transforms

# Standard ImageNet stats
imagenet_stats = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])


class IFilter(ABC):
    @abstractmethod
    def filter(
        self, orig_image: PilImage, filtered_image: PilImage, render_factor: int
    ) -> PilImage:
        pass


class BaseFilter(IFilter):
    def __init__(self, learn, stats: tuple = imagenet_stats):
        super().__init__()
        self.learn = learn
        self.device = self.learn.device
        self.norm_mean = torch.tensor(stats[0]).to(self.device).view(1, 3, 1, 1)
        self.norm_std = torch.tensor(stats[1]).to(self.device).view(1, 3, 1, 1)

    def _transform(self, image: PilImage) -> PilImage:
        return image

    def _scale_to_square(self, orig: PilImage, targ: int) -> PilImage:
        targ_sz = (targ, targ)
        return orig.resize(targ_sz, resample=PilImage.BILINEAR)

    def _get_model_ready_image(self, orig: PilImage, sz: int) -> PilImage:
        result = self._scale_to_square(orig, sz)
        result = self._transform(result)
        return result

    def _model_process(self, orig: PilImage, sz: int) -> PilImage:
        model_image = self._get_model_ready_image(orig, sz)

        # Convert to tensor (0-1 range)
        x = transforms.ToTensor()(model_image).unsqueeze(0).to(self.device)

        # Normalize
        x = (x - self.norm_mean) / self.norm_std

        try:
            with torch.no_grad():
                out = self.learn.model(x)
        except RuntimeError as rerr:
            if "memory" not in str(rerr):
                raise rerr
            logging.warn(
                "Warning: render_factor was set too high, and out of memory error resulted. Returning original image."
            )
            return model_image

        # Denormalize
        out = out * self.norm_std + self.norm_mean
        out = out.squeeze(0).clamp(0, 1)

        # Convert to PIL
        out_np = out.permute(1, 2, 0).cpu().numpy()
        out_np = (out_np * 255).astype(np.uint8)
        return PilImage.fromarray(out_np)

    def _unsquare(self, image: PilImage, orig: PilImage) -> PilImage:
        targ_sz = orig.size
        image = image.resize(targ_sz, resample=PilImage.BILINEAR)
        return image


class ColorizerFilter(BaseFilter):
    def __init__(self, learn, stats: tuple = imagenet_stats):
        super().__init__(learn=learn, stats=stats)
        self.render_base = 16

    def filter(
        self,
        orig_image: PilImage,
        filtered_image: PilImage,
        render_factor: int,
        post_process: bool = True,
    ) -> PilImage:
        render_sz = render_factor * self.render_base
        model_image = self._model_process(orig=filtered_image, sz=render_sz)
        raw_color = self._unsquare(model_image, orig_image)

        if post_process:
            return self._post_process(raw_color, orig_image)
        else:
            return raw_color

    def _transform(self, image: PilImage) -> PilImage:
        return image.convert("LA").convert("RGB")

    def _post_process(self, raw_color: PilImage, orig: PilImage) -> PilImage:
        color_np = np.asarray(raw_color)
        orig_np = np.asarray(orig)
        color_yuv = cv2.cvtColor(color_np, cv2.COLOR_RGB2YUV)
        # do a black and white transform first to get better luminance values
        orig_yuv = cv2.cvtColor(orig_np, cv2.COLOR_RGB2YUV)
        hires = np.copy(orig_yuv)
        hires[:, :, 1:3] = color_yuv[:, :, 1:3]
        final = cv2.cvtColor(hires, cv2.COLOR_YUV2RGB)
        final = PilImage.fromarray(final)
        return final


class MasterFilter(BaseFilter):
    def __init__(self, filters: List[IFilter], render_factor: int):
        self.filters = filters
        self.render_factor = render_factor

    def filter(
        self,
        orig_image: PilImage,
        filtered_image: PilImage,
        render_factor: int = None,
        post_process: bool = True,
    ) -> PilImage:
        render_factor = self.render_factor if render_factor is None else render_factor
        for filter in self.filters:
            filtered_image = filter.filter(
                orig_image, filtered_image, render_factor, post_process
            )

        return filtered_image
